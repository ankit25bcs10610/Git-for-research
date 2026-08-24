from app.db.models import LastSeen
from app.versioning.dag_store import get_branch_head, get_commit


def mark_seen(session, user_id: str, artifact_id: str, commit_ref: str) -> None:
    existing = (
        session.query(LastSeen)
        .filter(LastSeen.user_id == user_id, LastSeen.artifact_id == artifact_id)
        .one_or_none()
    )
    if existing is None:
        existing = LastSeen(
            user_id=user_id, artifact_id=artifact_id, commit_ref=commit_ref
        )
        session.add(existing)
    else:
        existing.commit_ref = commit_ref
    session.commit()


def get_changes_since(
    session, user_id: str, artifact_id: str, branch_name: str
) -> list:
    head_ref = get_branch_head(session, artifact_id, branch_name)
    if head_ref is None:
        return []

    last_seen_row = (
        session.query(LastSeen)
        .filter(LastSeen.user_id == user_id, LastSeen.artifact_id == artifact_id)
        .one_or_none()
    )
    stop_ref = last_seen_row.commit_ref if last_seen_row is not None else None

    commits = []
    current_ref = head_ref
    while current_ref is not None and current_ref != stop_ref:
        commit = get_commit(session, current_ref)
        if commit is None:
            break
        commits.append(commit)
        current_ref = commit.parent_ids[0] if commit.parent_ids else None

    commits.reverse()
    return commits
