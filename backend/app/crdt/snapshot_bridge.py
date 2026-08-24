from sqlalchemy.exc import IntegrityError

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
        try:
            create_branch(session, artifact_id, branch_name, new_commit_ref)
        except (ValueError, IntegrityError):
            # Another "first commit" for this same artifact/branch pair won
            # the race between our get_branch_head() read above and this
            # create_branch() call -- create_branch's own existence guard
            # raises ValueError for that; the branches table's unique
            # constraint (uq_branch_artifact_name) would raise IntegrityError
            # instead if two callers ever slipped past that guard at the same
            # instant. Either way, don't crash: the branch now exists
            # (created by that other writer), so roll back this failed
            # attempt and fall back to treating our already-created commit
            # the same way any normal, non-first commit is handled --
            # advance the branch to point at it. Both commits remain rows in
            # the commits table and are individually reachable by id; a full
            # reconciliation (re-parenting one commit under the other, or a
            # real merge of the two snapshots) is deliberately not attempted
            # here -- the goal for this rare race is "never raise, never
            # lose a row," not "always produce the ideal history."
            session.rollback()
            update_branch_head(session, artifact_id, branch_name, new_commit_ref)
    else:
        update_branch_head(session, artifact_id, branch_name, new_commit_ref)
    return new_commit_ref
