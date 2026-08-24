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
