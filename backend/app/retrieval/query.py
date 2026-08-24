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
