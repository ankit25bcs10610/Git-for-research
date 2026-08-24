import uuid

from app.crdt.snapshot_bridge import commit_snapshot
from app.versioning.dag_store import create_branch, get_branch_head, get_commit


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


def test_commit_snapshot_two_concurrent_first_commits_do_not_crash(db_session, monkeypatch):
    """Regression test for Finding C3.

    Simulates two "first commit" calls racing for the same new
    artifact/branch pair: both read `get_branch_head(...) is None`, both
    build their own commit with `parent_ids == []`, and both then attempt
    `create_branch`. Without a guard, this used to insert a second Branch
    row for the same (artifact_id, name), permanently breaking every later
    get_branch_head/update_branch_head call for that pair with
    MultipleResultsFound. `create_branch`'s new existence guard now raises
    ValueError for the loser of the race; `commit_snapshot` must catch that
    and recover rather than crash.

    Chosen behavior (documented, not the only valid choice): the writer
    whose `commit_snapshot` call reaches the `create_branch`/recovery step
    second "wins" the branch head -- it falls back to `update_branch_head`
    and becomes the new tip. The other writer's commit is not lost: it
    remains a real row in the commits table, individually reachable by id,
    just no longer pointed to by the branch. A full reconciliation (e.g.
    re-parenting one commit under the other) is out of scope for this rare
    race; the bar here is "never raise, never lose a row."
    """
    import app.crdt.snapshot_bridge as snapshot_bridge_module
    from app.versioning.dag_adapter import DagVersionedArtifact
    from app.versioning.diff_engine import tokenize_paragraphs

    artifact_id = str(uuid.uuid4())
    branch_name = "main"

    # The "concurrent" writer's own first commit, created directly (not
    # through commit_snapshot) so its ref is known up front for the
    # monkeypatch to interleave.
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    concurrent_commit_ref = artifact.commit(
        "Concurrent writer's paragraph.", "user-2", "Live edit snapshot", None
    )

    original_create_branch = snapshot_bridge_module.create_branch
    state = {"interleaved": False}

    def create_branch_with_interleaved_concurrent_writer(session, artifact_id_arg, name_arg, head_commit_id_arg):
        if not state["interleaved"]:
            state["interleaved"] = True
            # The concurrent writer's own create_branch call lands here,
            # between our get_branch_head() read (which returned None) and
            # our own create_branch() call below.
            original_create_branch(session, artifact_id_arg, name_arg, concurrent_commit_ref)
        return original_create_branch(session, artifact_id_arg, name_arg, head_commit_id_arg)

    monkeypatch.setattr(
        snapshot_bridge_module, "create_branch", create_branch_with_interleaved_concurrent_writer
    )

    assert get_branch_head(db_session, artifact_id, branch_name) is None

    # Must not raise.
    our_commit_ref = commit_snapshot(
        db_session, artifact_id, branch_name, "Our paragraph.", "user-1"
    )

    final_head = get_branch_head(db_session, artifact_id, branch_name)
    assert final_head is not None

    # Both commits are real, individually-reachable rows -- neither was
    # lost, even though only one of them ends up as the branch's head.
    assert get_commit(db_session, our_commit_ref) is not None
    assert get_commit(db_session, concurrent_commit_ref) is not None
    assert final_head in (our_commit_ref, concurrent_commit_ref)
