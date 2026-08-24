import uuid

from app.db.models import ProvenanceEdge


def add_provenance_edge(session, from_chunk_id: str, to_chunk_id: str, relation: str) -> None:
    edge = ProvenanceEdge(
        id=str(uuid.uuid4()),
        from_chunk_id=from_chunk_id,
        to_chunk_id=to_chunk_id,
        relation=relation,
    )
    session.add(edge)
    session.commit()


def trace_provenance(session, chunk_id: str) -> list[dict]:
    chain: list[dict] = []
    visited: set[str] = {chunk_id}
    current_id = chunk_id
    while True:
        edge = (
            session.query(ProvenanceEdge)
            .filter(ProvenanceEdge.from_chunk_id == current_id)
            .first()
        )
        if edge is None:
            break
        if edge.to_chunk_id in visited:
            break
        chain.append({"chunk_id": edge.to_chunk_id, "relation": edge.relation})
        visited.add(edge.to_chunk_id)
        current_id = edge.to_chunk_id
    return chain
