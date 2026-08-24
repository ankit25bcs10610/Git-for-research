import uuid

from app.crdt.snapshot_bridge import commit_snapshot
from app.versioning.dag_store import get_branch_head, get_commit


def test_commit_snapshot_creates_commit_and_advances_branch_head(db_session):
    artifact_id = str(uuid.uuid4())
    branch_name = "main"

    assert get_branch_head(db_session, artifact_id, branch_name) is None

    first_ref = commit_snapshot(
        db_session, artifact_id, branch_name, "Paragraph one.", "user-1"
    )

    assert get_branch_head(db_session, artifact_id, branch_name) == first_ref
    first_commit = get_commit(db_session, first_ref)
    assert first_commit.parent_ids == []
    assert first_commit.message == "Live edit snapshot"

    second_ref = commit_snapshot(
        db_session,
        artifact_id,
        branch_name,
        "Paragraph one.\n\nParagraph two.",
        "user-1",
    )

    assert second_ref != first_ref
    assert get_branch_head(db_session, artifact_id, branch_name) == second_ref
    second_commit = get_commit(db_session, second_ref)
    assert second_commit.parent_ids == [first_ref]
