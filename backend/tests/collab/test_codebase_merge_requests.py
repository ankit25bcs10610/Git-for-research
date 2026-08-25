import tempfile

from app.versioning.git_adapter import GitVersionedArtifact, init_repo_from_files
from app.db.models import MergeRequest


def _make_artifact():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n", "b.txt": "content b\n"})
    return GitVersionedArtifact(repo_path)


def test_create_merge_request_records_base_commit_ref_and_opened_by(db_session):
    from app.collab.codebase_merge_requests import create_merge_request

    artifact = _make_artifact()
    root = artifact.branch_head("master")
    artifact.branch("feature", "master")

    artifact.checkout_branch("feature")
    artifact.commit({"a.txt": "feature edit\n"}, "user-1", "edit on feature")

    mr_id = create_merge_request(db_session, artifact, "codebase-artifact-1", "feature", "master", "alice")

    mr = db_session.get(MergeRequest, mr_id)
    assert mr is not None
    assert mr.artifact_id == "codebase-artifact-1"
    assert mr.source_branch == "feature"
    assert mr.target_branch == "master"
    assert mr.status == "open"
    assert mr.base_commit_ref == root
    assert mr.opened_by == "alice"


def test_get_merge_request_diff_reports_no_conflicts_for_disjoint_edits(db_session):
    from app.collab.codebase_merge_requests import create_merge_request, get_merge_request_diff

    artifact = _make_artifact()
    artifact.branch("feature", "master")

    artifact.checkout_branch("feature")
    artifact.commit({"a.txt": "feature edit\n"}, "user-1", "edit a on feature")

    artifact.checkout_branch("master")
    artifact.commit({"b.txt": "master edit\n"}, "user-1", "edit b on master")

    mr_id = create_merge_request(db_session, artifact, "codebase-artifact-2", "feature", "master", "alice")
    result = get_merge_request_diff(db_session, artifact, mr_id)

    assert result["conflicts"] == []


def test_get_merge_request_diff_reports_a_conflict_and_does_not_mutate_the_repo(db_session):
    from app.collab.codebase_merge_requests import create_merge_request, get_merge_request_diff

    artifact = _make_artifact()
    artifact.branch("feature", "master")

    artifact.checkout_branch("feature")
    artifact.commit({"a.txt": "feature edit\n"}, "user-1", "edit a on feature")

    artifact.checkout_branch("master")
    master_head = artifact.commit({"a.txt": "master edit\n"}, "user-1", "edit a on master")

    mr_id = create_merge_request(db_session, artifact, "codebase-artifact-3", "feature", "master", "alice")
    result = get_merge_request_diff(db_session, artifact, mr_id)

    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0]["path"] == "a.txt"
    assert artifact.branch_head("master") == master_head


def test_merge_merge_request_advances_target_branch_when_no_conflicts(db_session):
    from app.collab.codebase_merge_requests import create_merge_request, merge_merge_request

    artifact = _make_artifact()
    artifact.branch("feature", "master")

    artifact.checkout_branch("feature")
    artifact.commit({"a.txt": "feature edit\n"}, "user-1", "edit a on feature")

    artifact.checkout_branch("master")
    old_head = artifact.branch_head("master")

    mr_id = create_merge_request(db_session, artifact, "codebase-artifact-4", "feature", "master", "alice")
    result = merge_merge_request(db_session, artifact, mr_id, None, "bob")

    mr = db_session.get(MergeRequest, mr_id)
    assert result is True
    assert mr.status == "merged"
    assert mr.merged_by == "bob"
    assert artifact.branch_head("master") != old_head
    assert artifact.get_content("master")["a.txt"] == "feature edit\n"


def test_merge_merge_request_blocks_on_conflict_until_resolved(db_session):
    from app.collab.codebase_merge_requests import (
        create_merge_request,
        get_merge_request_diff,
        merge_merge_request,
    )

    artifact = _make_artifact()
    artifact.branch("feature", "master")

    artifact.checkout_branch("feature")
    artifact.commit({"a.txt": "feature edit\n"}, "user-1", "edit a on feature")

    artifact.checkout_branch("master")
    artifact.commit({"a.txt": "master edit\n"}, "user-1", "edit a on master")

    mr_id = create_merge_request(db_session, artifact, "codebase-artifact-5", "feature", "master", "alice")

    blocked = merge_merge_request(db_session, artifact, mr_id, None, "bob")
    mr = db_session.get(MergeRequest, mr_id)
    assert blocked is False
    assert mr.status == "open"

    diff_result = get_merge_request_diff(db_session, artifact, mr_id)
    conflict_path = diff_result["conflicts"][0]["path"]

    resolved = merge_merge_request(
        db_session, artifact, mr_id, {conflict_path: "resolved content\n"}, "bob"
    )
    mr = db_session.get(MergeRequest, mr_id)
    assert resolved is True
    assert mr.status == "merged"
    assert artifact.get_content("master")["a.txt"] == "resolved content\n"


def test_merge_merge_request_on_already_merged_mr_returns_false(db_session):
    from app.collab.codebase_merge_requests import create_merge_request, merge_merge_request

    artifact = _make_artifact()
    artifact.branch("feature", "master")

    artifact.checkout_branch("feature")
    artifact.commit({"a.txt": "feature edit\n"}, "user-1", "edit a on feature")

    mr_id = create_merge_request(db_session, artifact, "codebase-artifact-6", "feature", "master", "alice")

    first = merge_merge_request(db_session, artifact, mr_id, None, "bob")
    assert first is True

    second = merge_merge_request(db_session, artifact, mr_id, None, "bob")
    assert second is False


def test_reject_merge_request_records_rejected_by(db_session):
    from app.collab.codebase_merge_requests import create_merge_request, reject_merge_request

    artifact = _make_artifact()
    artifact.branch("feature", "master")

    mr_id = create_merge_request(db_session, artifact, "codebase-artifact-7", "feature", "master", "alice")
    reject_merge_request(db_session, mr_id, "carol")

    mr = db_session.get(MergeRequest, mr_id)
    assert mr.status == "rejected"
    assert mr.rejected_by == "carol"
