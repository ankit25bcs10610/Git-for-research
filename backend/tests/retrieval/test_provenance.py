import uuid

from app.db.base import get_session
from app.retrieval.query import index_chunks
from app.retrieval.provenance import add_provenance_edge, trace_provenance


def test_trace_provenance_returns_two_hop_chain_in_order():
    with get_session() as session:
        artifact_id = str(uuid.uuid4())
        commit_ref = str(uuid.uuid4())
        chunk_ids = index_chunks(
            session,
            artifact_id,
            commit_ref,
            ["Claim A", "Source B", "Source C"],
        )
        chunk_a, chunk_b, chunk_c = chunk_ids
        add_provenance_edge(session, chunk_a, chunk_b, "cites")
        add_provenance_edge(session, chunk_b, chunk_c, "supports")

        chain = trace_provenance(session, chunk_a)

        assert chain == [
            {"chunk_id": chunk_b, "relation": "cites"},
            {"chunk_id": chunk_c, "relation": "supports"},
        ]


def test_trace_provenance_returns_empty_list_when_no_edges_exist():
    with get_session() as session:
        artifact_id = str(uuid.uuid4())
        commit_ref = str(uuid.uuid4())
        chunk_ids = index_chunks(session, artifact_id, commit_ref, ["Standalone claim"])
        chunk_id = chunk_ids[0]

        chain = trace_provenance(session, chunk_id)

        assert chain == []


def test_trace_provenance_handles_a_cycle_without_infinite_loop():
    with get_session() as session:
        artifact_id = str(uuid.uuid4())
        commit_ref = str(uuid.uuid4())
        chunk_ids = index_chunks(session, artifact_id, commit_ref, ["Claim A", "Claim B"])
        chunk_a, chunk_b = chunk_ids
        add_provenance_edge(session, chunk_a, chunk_b, "cites")
        add_provenance_edge(session, chunk_b, chunk_a, "cites")

        chain = trace_provenance(session, chunk_a)

        assert chain == [{"chunk_id": chunk_b, "relation": "cites"}]
