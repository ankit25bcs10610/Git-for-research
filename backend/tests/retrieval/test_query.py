import uuid

from app.db.base import get_session
from app.db.models import Chunk
from app.retrieval.query import index_chunks


def test_index_chunks_creates_distinct_chunk_rows():
    artifact_id = str(uuid.uuid4())
    commit_ref = str(uuid.uuid4())
    texts = [
        "The cat sat on the mat.",
        "Quarterly revenue grew by ten percent this year.",
        "The dog played in the park all afternoon.",
    ]
    with get_session() as session:
        chunk_ids = index_chunks(session, artifact_id, commit_ref, texts)
        assert len(chunk_ids) == 3
        assert len(set(chunk_ids)) == 3
        stored = session.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
        assert len(stored) == 3
        assert {row.artifact_id for row in stored} == {artifact_id}
