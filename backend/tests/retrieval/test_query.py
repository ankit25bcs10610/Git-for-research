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


from app.retrieval.query import similarity_search


def test_similarity_search_ranks_semantically_closest_chunk_first():
    artifact_id = str(uuid.uuid4())
    commit_ref = str(uuid.uuid4())
    texts = [
        "The cat sat on the mat.",
        "Quarterly revenue grew by ten percent this year.",
        "The dog played in the park all afternoon.",
    ]
    with get_session() as session:
        index_chunks(session, artifact_id, commit_ref, texts)
        results = similarity_search(session, "A feline is resting on a rug.", top_k=3)
        assert results[0]["text"] == "The cat sat on the mat."
        assert results[0]["artifact_id"] == artifact_id
        assert results[0]["commit_ref"] == commit_ref
        assert "chunk_id" in results[0]
        assert "score" in results[0]
