from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.dag_store import create_branch, get_branch_head, update_branch_head
from app.versioning.diff_engine import tokenize_paragraphs


def commit_snapshot(
    session, artifact_id: str, branch_name: str, snapshot_text: str, author: str
) -> str:
    parent_ref = get_branch_head(session, artifact_id, branch_name)
    artifact = DagVersionedArtifact(session, artifact_id, tokenize_paragraphs)
    new_commit_ref = artifact.commit(
        snapshot_text, author, "Live edit snapshot", parent_ref
    )
    # dag_store.update_branch_head only updates an existing Branch row and
    # raises ValueError if none exists yet; the brief's version called it
    # unconditionally, which breaks on a brand-new artifact/branch pair (no
    # Branch row yet). Create the branch on the first commit (parent_ref is
    # None means no branch head existed) and update it on subsequent commits.
    if parent_ref is None:
        create_branch(session, artifact_id, branch_name, new_commit_ref)
    else:
        update_branch_head(session, artifact_id, branch_name, new_commit_ref)
    return new_commit_ref
