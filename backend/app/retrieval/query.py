import uuid

from app.db.models import Chunk
from app.retrieval.embeddings import embed_text


def index_chunks(session, artifact_id: str, commit_ref: str, texts: list[str]) -> list[str]:
    chunk_ids: list[str] = []
    for index, text in enumerate(texts):
        chunk_id = str(uuid.uuid4())
        chunk = Chunk(
            id=chunk_id,
            artifact_id=artifact_id,
            commit_ref=commit_ref,
            text=text,
            embedding=embed_text(text),
            span=str(index),
        )
        session.add(chunk)
        chunk_ids.append(chunk_id)
    session.commit()
    return chunk_ids


def similarity_search(session, query: str, top_k: int = 5) -> list[dict]:
    query_embedding = embed_text(query)
    distance = Chunk.embedding.cosine_distance(query_embedding)
    rows = (
        session.query(Chunk, distance.label("distance"))
        .order_by(distance)
        .limit(top_k)
        .all()
    )
    results: list[dict] = []
    for chunk, score in rows:
        results.append(
            {
                "chunk_id": chunk.id,
                "text": chunk.text,
                "artifact_id": chunk.artifact_id,
                "commit_ref": chunk.commit_ref,
                "score": float(score),
            }
        )
    return results
