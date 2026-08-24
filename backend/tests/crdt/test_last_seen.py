import uuid

from app.crdt.last_seen import get_changes_since, mark_seen
from app.crdt.snapshot_bridge import commit_snapshot


def test_get_changes_since_with_no_last_seen_returns_full_history(db_session):
    artifact_id = str(uuid.uuid4())
    branch_name = "main"

    commit_snapshot(db_session, artifact_id, branch_name, "Paragraph one.", "user-1")
    commit_snapshot(
        db_session,
        artifact_id,
        branch_name,
        "Paragraph one.\n\nParagraph two.",
        "user-1",
    )

    changes = get_changes_since(db_session, "user-1", artifact_id, branch_name)

    assert len(changes) == 2
    assert changes[0].parent_ids == []
    assert changes[1].parent_ids == [changes[0].id]


def test_get_changes_since_after_mark_seen_returns_only_new_commits(db_session):
    artifact_id = str(uuid.uuid4())
    branch_name = "main"

    first_ref = commit_snapshot(db_session, artifact_id, branch_name, "Paragraph one.", "user-1")
    mark_seen(db_session, "user-1", artifact_id, first_ref)

    second_ref = commit_snapshot(
        db_session,
        artifact_id,
        branch_name,
        "Paragraph one.\n\nParagraph two.",
        "user-1",
    )

    changes = get_changes_since(db_session, "user-1", artifact_id, branch_name)

    assert len(changes) == 1
    assert changes[0].id == second_ref
