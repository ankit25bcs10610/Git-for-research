import uuid

from app.db.base import get_session
from app.db.models import Blob
from app.versioning.dag_store import create_blob, get_blob_content


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
