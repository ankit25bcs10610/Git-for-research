import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.base import get_session
from app.db.models import Blob, Branch
from app.versioning.dag_store import (
    create_blob,
    get_blob_content,
    create_commit,
    get_commit,
    create_branch,
    get_branch_head,
    update_branch_head,
)


def test_create_blob_dedups_and_different_content_gets_different_hash():
    content_a = f"paragraph one {uuid.uuid4()}"
    content_b = f"paragraph two {uuid.uuid4()}"

    with get_session() as session:
        hash_a1 = create_blob(session, content_a)
        hash_a2 = create_blob(session, content_a)
        hash_b = create_blob(session, content_b)

        assert hash_a1 == hash_a2
        assert hash_a1 != hash_b

        rows = session.query(Blob).filter(Blob.hash == hash_a1).all()
        assert len(rows) == 1

        assert get_blob_content(session, hash_a1) == content_a


def test_create_commit_stores_parent_ids_and_get_commit_retrieves_it():
    artifact_id = str(uuid.uuid4())

    with get_session() as session:
        parent_blob_hash = create_blob(session, f"root content {uuid.uuid4()}")
        parent_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=parent_blob_hash,
            parent_ids=[],
            author="user-1",
            message="initial commit",
        )

        child_blob_hash = create_blob(session, f"child content {uuid.uuid4()}")
        child_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=child_blob_hash,
            parent_ids=[parent_commit_id],
            author="user-1",
            message="second commit",
        )

        fetched = get_commit(session, child_commit_id)

        assert fetched.id == child_commit_id
        assert fetched.artifact_id == artifact_id
        assert fetched.parent_ids == [parent_commit_id]
        assert fetched.blob_hash == child_blob_hash
        assert fetched.author == "user-1"
        assert fetched.message == "second commit"


def test_create_branch_and_get_branch_head():
    artifact_id = str(uuid.uuid4())
    branch_name = f"main-{uuid.uuid4()}"

    with get_session() as session:
        blob_hash = create_blob(session, f"branch content {uuid.uuid4()}")
        commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=blob_hash,
            parent_ids=[],
            author="user-1",
            message="initial commit",
        )

        create_branch(session, artifact_id=artifact_id, name=branch_name, head_commit_id=commit_id)

        assert get_branch_head(session, artifact_id=artifact_id, name=branch_name) == commit_id


def test_get_branch_head_returns_none_for_missing_branch():
    artifact_id = str(uuid.uuid4())

    with get_session() as session:
        assert get_branch_head(session, artifact_id=artifact_id, name="does-not-exist") is None


def test_update_branch_head_updates_pointer():
    artifact_id = str(uuid.uuid4())
    branch_name = f"main-{uuid.uuid4()}"

    with get_session() as session:
        first_blob_hash = create_blob(session, f"first content {uuid.uuid4()}")
        first_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=first_blob_hash,
            parent_ids=[],
            author="user-1",
            message="first commit",
        )
        create_branch(session, artifact_id=artifact_id, name=branch_name, head_commit_id=first_commit_id)

        second_blob_hash = create_blob(session, f"second content {uuid.uuid4()}")
        second_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=second_blob_hash,
            parent_ids=[first_commit_id],
            author="user-1",
            message="second commit",
        )

        update_branch_head(session, artifact_id=artifact_id, name=branch_name, new_commit_id=second_commit_id)

        assert get_branch_head(session, artifact_id=artifact_id, name=branch_name) == second_commit_id


def test_update_branch_head_cas_succeeds_when_expected_matches_current_head():
    artifact_id = str(uuid.uuid4())
    branch_name = f"main-{uuid.uuid4()}"

    with get_session() as session:
        first_blob_hash = create_blob(session, f"first content {uuid.uuid4()}")
        first_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=first_blob_hash,
            parent_ids=[],
            author="user-1",
            message="first commit",
        )
        create_branch(session, artifact_id=artifact_id, name=branch_name, head_commit_id=first_commit_id)

        second_blob_hash = create_blob(session, f"second content {uuid.uuid4()}")
        second_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=second_blob_hash,
            parent_ids=[first_commit_id],
            author="user-1",
            message="second commit",
        )

        result = update_branch_head(
            session,
            artifact_id=artifact_id,
            name=branch_name,
            new_commit_id=second_commit_id,
            expected_commit_id=first_commit_id,
        )

        assert result is True
        assert get_branch_head(session, artifact_id=artifact_id, name=branch_name) == second_commit_id


def test_update_branch_head_cas_fails_and_leaves_head_unchanged_when_expected_is_stale():
    artifact_id = str(uuid.uuid4())
    branch_name = f"main-{uuid.uuid4()}"

    with get_session() as session:
        first_blob_hash = create_blob(session, f"first content {uuid.uuid4()}")
        first_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=first_blob_hash,
            parent_ids=[],
            author="user-1",
            message="first commit",
        )
        create_branch(session, artifact_id=artifact_id, name=branch_name, head_commit_id=first_commit_id)

        # Someone else already moved the head to `second_commit_id`...
        second_blob_hash = create_blob(session, f"second content {uuid.uuid4()}")
        second_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=second_blob_hash,
            parent_ids=[first_commit_id],
            author="user-1",
            message="second commit",
        )
        update_branch_head(session, artifact_id=artifact_id, name=branch_name, new_commit_id=second_commit_id)

        # ...so a stale writer that still expects `first_commit_id` must lose
        # the race rather than clobber the branch.
        third_blob_hash = create_blob(session, f"third content {uuid.uuid4()}")
        third_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=third_blob_hash,
            parent_ids=[first_commit_id],
            author="user-1",
            message="third commit",
        )

        result = update_branch_head(
            session,
            artifact_id=artifact_id,
            name=branch_name,
            new_commit_id=third_commit_id,
            expected_commit_id=first_commit_id,
        )

        assert result is False
        assert get_branch_head(session, artifact_id=artifact_id, name=branch_name) == second_commit_id


def test_create_branch_raises_on_duplicate_artifact_and_branch_name(db_session):
    """Regression test for Finding C3.

    A plain sequential double-submit (e.g. a double-click) must not create
    a second Branch row for the same (artifact_id, name) -- that used to
    make every later get_branch_head/update_branch_head for that
    artifact+branch raise MultipleResultsFound permanently, with no
    recovery path. create_branch's own existence guard must now reject the
    second call with a clear error rather than silently inserting a
    duplicate.
    """
    artifact_id = str(uuid.uuid4())
    branch_name = "main"

    blob_hash = create_blob(db_session, f"root content {uuid.uuid4()}")
    commit_id = create_commit(
        db_session,
        artifact_id=artifact_id,
        blob_hash=blob_hash,
        parent_ids=[],
        author="user-1",
        message="initial commit",
    )

    create_branch(db_session, artifact_id=artifact_id, name=branch_name, head_commit_id=commit_id)

    with pytest.raises(ValueError):
        create_branch(db_session, artifact_id=artifact_id, name=branch_name, head_commit_id=commit_id)

    # Exactly one Branch row for this (artifact_id, name) -- no duplicate
    # was silently inserted by the second call.
    rows = (
        db_session.query(Branch)
        .filter_by(artifact_id=artifact_id, name=branch_name)
        .all()
    )
    assert len(rows) == 1


def test_branch_unique_constraint_rejects_duplicate_row_at_db_level(db_session):
    """Regression test for Finding C3.

    Proves the DB-level unique constraint (uq_branch_artifact_name) itself
    is the real backstop, not just create_branch's application-level guard.
    Bypasses create_branch entirely and inserts a second Branch row directly
    via the model, simulating a race that slips past an application-level
    check -- this must be rejected by the database with IntegrityError.
    """
    artifact_id = str(uuid.uuid4())
    branch_name = "main"

    first = Branch(
        id=str(uuid.uuid4()),
        artifact_id=artifact_id,
        name=branch_name,
        head_commit_id="commit-a",
    )
    db_session.add(first)
    db_session.commit()

    second = Branch(
        id=str(uuid.uuid4()),
        artifact_id=artifact_id,
        name=branch_name,
        head_commit_id="commit-b",
    )
    db_session.add(second)
    with pytest.raises(IntegrityError):
        db_session.commit()

    # Leave the session in a usable state for the fixture's own teardown.
    db_session.rollback()
