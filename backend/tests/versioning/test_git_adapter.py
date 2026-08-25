import os
import tempfile

from app.versioning.git_adapter import GitVersionedArtifact, clone_repo, init_repo_from_files


def test_init_repo_from_files_creates_initial_commit():
    repo_path = tempfile.mkdtemp()

    init_repo_from_files(repo_path, {"a.txt": "content a\n", "b.txt": "content b\n"})

    assert os.path.isdir(os.path.join(repo_path, ".git"))
    assert open(os.path.join(repo_path, "a.txt")).read() == "content a\n"
    assert open(os.path.join(repo_path, "b.txt")).read() == "content b\n"


def test_clone_repo_preserves_content_and_history():
    source_path = tempfile.mkdtemp()
    init_repo_from_files(source_path, {"readme.md": "hello\n"})

    dest_path = tempfile.mkdtemp()
    clone_repo(source_path, dest_path)

    assert os.path.isdir(os.path.join(dest_path, ".git"))
    assert open(os.path.join(dest_path, "readme.md")).read() == "hello\n"


def test_commit_writes_new_file_and_returns_commit_id():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n"})

    artifact = GitVersionedArtifact(repo_path)
    commit_id = artifact.commit(
        {"a.txt": "content a changed\n"}, "user-1", "edit a"
    )

    assert isinstance(commit_id, str)
    assert len(commit_id) == 40
    assert open(os.path.join(repo_path, "a.txt")).read() == "content a changed\n"


def test_diff_reports_added_removed_and_modified_paths():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(
        repo_path, {"a.txt": "content a\n", "b.txt": "content b\n"}
    )
    artifact = GitVersionedArtifact(repo_path)
    first_commit = artifact.commit(None, "user-1", "noop")

    os.remove(os.path.join(repo_path, "b.txt"))
    second_commit = artifact.commit(
        {"a.txt": "content a changed\n", "c.txt": "content c\n"},
        "user-1",
        "modify a, add c, remove b",
    )

    changes = artifact.diff(first_commit, second_commit)
    changes_by_path = {change["path"]: change["status"] for change in changes}

    assert changes_by_path == {
        "a.txt": "modified",
        "b.txt": "removed",
        "c.txt": "added",
    }


def test_branch_creates_ref_pointing_at_given_commit():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n"})
    artifact = GitVersionedArtifact(repo_path)
    first_commit = artifact.commit(None, "user-1", "noop")

    artifact.branch("feature", "master")

    assert artifact.branch_head("feature") == first_commit


def test_checkout_branch_switches_head_and_working_tree():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n"})
    artifact = GitVersionedArtifact(repo_path)
    artifact.branch("feature", "master")

    artifact.commit({"a.txt": "content a on master\n"}, "user-1", "edit on master")
    artifact.checkout_branch("feature")

    assert artifact.repo.head.shorthand == "feature"
    assert open(os.path.join(repo_path, "a.txt")).read() == "content a\n"


def test_get_content_returns_all_blobs_at_a_commit():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(
        repo_path, {"a.txt": "content a\n", "b.txt": "content b\n"}
    )
    artifact = GitVersionedArtifact(repo_path)
    commit_id = artifact.commit(None, "user-1", "noop")

    content = artifact.get_content(commit_id)

    assert content == {"a.txt": "content a\n", "b.txt": "content b\n"}


def test_merge_without_conflicts_combines_both_branches_edits():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(
        repo_path, {"a.txt": "content a\n", "b.txt": "content b\n"}
    )
    artifact = GitVersionedArtifact(repo_path)
    artifact.branch("feature", "master")
    base_ref = artifact.branch_head("feature")

    artifact.checkout_branch("feature")
    artifact.commit({"a.txt": "content a edited on feature\n"}, "user-1", "edit a on feature")

    artifact.checkout_branch("master")
    artifact.commit({"b.txt": "content b edited on master\n"}, "user-1", "edit b on master")

    result = artifact.merge(base_ref, "master", "feature")

    assert result["merged"] is True
    assert result["conflicts"] == []
    merged_content = artifact.get_content("master")
    assert merged_content["a.txt"] == "content a edited on feature\n"
    assert merged_content["b.txt"] == "content b edited on master\n"


def test_merge_without_conflicts_leaves_working_tree_and_index_in_sync():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(
        repo_path, {"a.txt": "content a\n", "b.txt": "content b\n"}
    )
    artifact = GitVersionedArtifact(repo_path)
    artifact.branch("feature", "master")
    base_ref = artifact.branch_head("feature")

    artifact.checkout_branch("feature")
    artifact.commit({"a.txt": "content a edited on feature\n"}, "user-1", "edit a on feature")

    artifact.checkout_branch("master")
    artifact.commit({"b.txt": "content b edited on master\n"}, "user-1", "edit b on master")

    result = artifact.merge(base_ref, "master", "feature")
    assert result["merged"] is True

    # A no-op commit right after the merge re-stages whatever is physically on
    # disk. If the working directory/index were not synced to the merge tree,
    # this would silently revert the feature branch's edit.
    artifact.commit(None, "user-1", "noop after merge")

    merged_content = artifact.get_content("master")
    assert merged_content["a.txt"] == "content a edited on feature\n"
    assert merged_content["b.txt"] == "content b edited on master\n"


def test_merge_with_conflicting_edits_returns_single_conflict():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n"})
    artifact = GitVersionedArtifact(repo_path)
    artifact.branch("feature", "master")
    base_ref = artifact.branch_head("feature")

    artifact.checkout_branch("feature")
    artifact.commit({"a.txt": "feature version of a\n"}, "user-1", "edit a on feature")

    artifact.checkout_branch("master")
    artifact.commit({"a.txt": "master version of a\n"}, "user-1", "edit a on master")

    result = artifact.merge(base_ref, "master", "feature")

    assert result["merged"] is False
    assert len(result["conflicts"]) == 1
    conflict = result["conflicts"][0]
    assert conflict["path"] == "a.txt"
    assert conflict["ours"] == "master version of a\n"
    assert conflict["theirs"] == "feature version of a\n"
    assert conflict["base"] == "content a\n"


def test_list_branches_returns_all_local_branch_names():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n"})
    artifact = GitVersionedArtifact(repo_path)
    artifact.branch("feature", "master")

    assert set(artifact.list_branches()) == {"master", "feature"}


def test_merge_base_returns_the_common_ancestor_commit():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n"})
    artifact = GitVersionedArtifact(repo_path)
    root_commit = artifact.branch_head("master")
    artifact.branch("feature", "master")

    artifact.checkout_branch("feature")
    artifact.commit({"a.txt": "feature version\n"}, "user-1", "edit on feature")

    artifact.checkout_branch("master")
    artifact.commit({"a.txt": "master version\n"}, "user-1", "edit on master")

    assert artifact.merge_base("master", "feature") == root_commit


def test_preview_merge_reports_conflicts_without_mutating_the_repo():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n"})
    artifact = GitVersionedArtifact(repo_path)
    artifact.branch("feature", "master")
    base_ref = artifact.branch_head("feature")

    artifact.checkout_branch("feature")
    artifact.commit({"a.txt": "feature version\n"}, "user-1", "edit on feature")

    artifact.checkout_branch("master")
    master_head = artifact.commit({"a.txt": "master version\n"}, "user-1", "edit on master")

    result = artifact.preview_merge(base_ref, "master", "feature")

    assert result["conflicts"][0]["path"] == "a.txt"
    # Must be read-only: branch head unchanged, no new commit written.
    assert artifact.branch_head("master") == master_head


def test_preview_merge_reports_no_conflicts_for_disjoint_edits():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n", "b.txt": "content b\n"})
    artifact = GitVersionedArtifact(repo_path)
    artifact.branch("feature", "master")
    base_ref = artifact.branch_head("feature")

    artifact.checkout_branch("feature")
    artifact.commit({"a.txt": "content a edited on feature\n"}, "user-1", "edit a on feature")

    artifact.checkout_branch("master")
    artifact.commit({"b.txt": "content b edited on master\n"}, "user-1", "edit b on master")

    result = artifact.preview_merge(base_ref, "master", "feature")

    assert result["conflicts"] == []


def test_merge_with_resolutions_for_every_conflicting_path_commits_the_resolved_content():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n"})
    artifact = GitVersionedArtifact(repo_path)
    artifact.branch("feature", "master")
    base_ref = artifact.branch_head("feature")

    artifact.checkout_branch("feature")
    feature_commit = artifact.commit({"a.txt": "feature version\n"}, "user-1", "edit on feature")

    artifact.checkout_branch("master")
    master_commit = artifact.commit({"a.txt": "master version\n"}, "user-1", "edit on master")

    result = artifact.merge(base_ref, "master", "feature", resolutions={"a.txt": "resolved version\n"})

    assert result["merged"] is True
    merged_content = artifact.get_content("master")
    assert merged_content["a.txt"] == "resolved version\n"
    merge_commit_id = artifact.branch_head("master")
    merge_commit = artifact.repo[merge_commit_id]
    assert {str(p) for p in merge_commit.parent_ids} == {master_commit, feature_commit}


def test_merge_with_incomplete_resolutions_stays_blocked():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n", "b.txt": "content b\n"})
    artifact = GitVersionedArtifact(repo_path)
    artifact.branch("feature", "master")
    base_ref = artifact.branch_head("feature")

    artifact.checkout_branch("feature")
    artifact.commit(
        {"a.txt": "feature a\n", "b.txt": "feature b\n"}, "user-1", "edit both on feature"
    )

    artifact.checkout_branch("master")
    master_commit = artifact.commit(
        {"a.txt": "master a\n", "b.txt": "master b\n"}, "user-1", "edit both on master"
    )

    # Only resolving one of the two conflicting paths.
    result = artifact.merge(base_ref, "master", "feature", resolutions={"a.txt": "resolved a\n"})

    assert result["merged"] is False
    assert len(result["conflicts"]) == 2
    assert artifact.branch_head("master") == master_commit
