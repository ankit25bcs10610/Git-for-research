from app.collab.merge_requests import create_merge_request
from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.dag_store import get_branch_head
from app.versioning.diff_engine import tokenize_paragraphs
from app.db.models import MergeRequest


def test_create_merge_request_records_base_commit_ref(db_session):
    artifact_id = "artifact-mr-1"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-a", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )

    mr_id = create_merge_request(db_session, artifact_id, "feature-a", "main")

    mr = db_session.get(MergeRequest, mr_id)
    assert mr is not None
    assert mr.artifact_id == artifact_id
    assert mr.source_branch == "feature-a"
    assert mr.target_branch == "main"
    assert mr.status == "open"
    assert mr.base_commit_ref == get_branch_head(db_session, artifact_id, "main")


def test_get_merge_request_diff_reports_no_conflicts_for_disjoint_edits(db_session):
    from app.collab.merge_requests import create_merge_request, get_merge_request_diff
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-2"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-b", root)

    # Committing alone does not move a branch head — DagVersionedArtifact.commit
    # only appends a commit object; the branch pointer must be advanced
    # explicitly so later branch-head lookups see this edit.
    feature_commit = artifact.commit(
        "Edited intro paragraph.\n\nBody paragraph.", "user-1", "edit intro", root
    )
    update_branch_head(db_session, artifact_id, "feature-b", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-b", "main")
    result = get_merge_request_diff(db_session, mr_id)

    assert result["conflicts"] == []


def test_merge_merge_request_advances_target_head_when_no_conflicts(db_session):
    from app.collab.merge_requests import create_merge_request, merge_merge_request
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-3"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-c", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )
    update_branch_head(db_session, artifact_id, "feature-c", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-c", "main")
    old_head = get_branch_head(db_session, artifact_id, "main")

    result = merge_merge_request(db_session, mr_id, None)

    new_head = get_branch_head(db_session, artifact_id, "main")
    mr = db_session.get(MergeRequest, mr_id)

    assert result is True
    assert new_head != old_head
    assert mr.status == "merged"
    assert artifact.get_content(new_head) == "Intro paragraph.\n\nEdited body paragraph."


def test_merge_merge_request_blocks_on_conflict_until_resolved(db_session):
    from app.collab.merge_requests import (
        create_merge_request,
        get_merge_request_diff,
        merge_merge_request,
    )
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-4"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-d", root)

    main_commit = artifact.commit(
        "Intro paragraph.\n\nMain-edited body.", "user-1", "main edit", root
    )
    update_branch_head(db_session, artifact_id, "main", main_commit)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nFeature-edited body.", "user-1", "feature edit", root
    )
    update_branch_head(db_session, artifact_id, "feature-d", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-d", "main")

    diff_result = get_merge_request_diff(db_session, mr_id)
    assert len(diff_result["conflicts"]) == 1

    blocked = merge_merge_request(db_session, mr_id, None)
    mr = db_session.get(MergeRequest, mr_id)
    assert blocked is False
    assert mr.status == "open"

    conflict_position = diff_result["conflicts"][0]["position"]
    resolved = merge_merge_request(
        db_session, mr_id, {conflict_position: "Resolved merged body."}
    )
    mr = db_session.get(MergeRequest, mr_id)
    assert resolved is True
    assert mr.status == "merged"

    new_head = get_branch_head(db_session, artifact_id, "main")
    assert artifact.get_content(new_head) == "Intro paragraph.\n\nResolved merged body."
