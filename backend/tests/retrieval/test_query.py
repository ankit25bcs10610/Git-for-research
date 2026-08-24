import uuid

from app.db.models import Chunk
from app.retrieval.query import index_chunks, similarity_search


def test_index_chunks_creates_distinct_chunk_rows(db_session):
    artifact_id = str(uuid.uuid4())
    commit_ref = str(uuid.uuid4())
    texts = [
        "The cat sat on the mat.",
        "Quarterly revenue grew by ten percent this year.",
        "The dog played in the park all afternoon.",
    ]
    chunk_ids = index_chunks(db_session, artifact_id, commit_ref, texts)
    assert len(chunk_ids) == 3
    assert len(set(chunk_ids)) == 3
    stored = db_session.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
    assert len(stored) == 3
    assert {row.artifact_id for row in stored} == {artifact_id}


def test_similarity_search_ranks_semantically_closest_chunk_first(db_session):
    artifact_id = str(uuid.uuid4())
    commit_ref = str(uuid.uuid4())
    texts = [
        "The cat sat on the mat.",
        "Quarterly revenue grew by ten percent this year.",
        "The dog played in the park all afternoon.",
    ]
    index_chunks(db_session, artifact_id, commit_ref, texts)
    results = similarity_search(db_session, "A feline is resting on a rug.", top_k=3)
    assert results[0]["text"] == "The cat sat on the mat."
    assert results[0]["artifact_id"] == artifact_id
    assert results[0]["commit_ref"] == commit_ref
    assert "chunk_id" in results[0]
    assert "score" in results[0]
