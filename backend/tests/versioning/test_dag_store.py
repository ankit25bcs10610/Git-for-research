import uuid

from app.db.base import get_session
from app.db.models import Blob
from app.versioning.dag_store import (
    create_blob,
    get_blob_content,
    create_commit,
    get_commit,
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
