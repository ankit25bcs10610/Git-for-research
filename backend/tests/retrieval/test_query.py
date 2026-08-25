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


def test_index_chunks_stores_the_span_label_for_code_chunk_tuples(db_session):
    """chunk_code() returns (span_label, text) tuples (e.g. "main.py::add")
    instead of plain strings -- index_chunks must store that label as the
    chunk's `span` instead of falling back to a bare numeric index.
    """
    artifact_id = str(uuid.uuid4())
    commit_ref = str(uuid.uuid4())
    code_chunks = [
        ("main.py::add", "def add(a, b):\n    return a + b\n"),
        ("main.py", "def add(a, b):\n    return a + b\n"),
    ]
    chunk_ids = index_chunks(db_session, artifact_id, commit_ref, code_chunks)
    stored = {row.id: row for row in db_session.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()}
    spans = {stored[cid].span for cid in chunk_ids}
    assert spans == {"main.py::add", "main.py"}


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
