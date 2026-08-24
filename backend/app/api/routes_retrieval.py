from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, tokenizer_for_type
from app.artifacts import get_artifact
from app.retrieval.chunker import chunk_messages, chunk_prose
from app.retrieval.provenance import add_provenance_edge, trace_provenance
from app.retrieval.query import index_chunks, similarity_search
from app.versioning.dag_adapter import DagVersionedArtifact

router = APIRouter()


class IndexRequest(BaseModel):
    commit_ref: str


class ProvenanceRequest(BaseModel):
    to_chunk_id: str
    relation: str


@router.get("/search")
def search_route(q: str, top_k: int = 5, db: Session = Depends(get_db)):
    results = similarity_search(db, q, top_k)
    return [
        {
            "chunk_id": r["chunk_id"],
            "text": r["text"],
            "artifact_id": r["artifact_id"],
            "commit_ref": r["commit_ref"],
            "score": r["score"],
        }
        for r in results
    ]


@router.post("/artifacts/{artifact_id}/index")
def index_route(artifact_id: str, body: IndexRequest, db: Session = Depends(get_db)):
    a = get_artifact(db, artifact_id)
    artifact = DagVersionedArtifact(db, artifact_id, tokenizer_for_type(a.type))
    content = artifact.get_content(body.commit_ref)
    chunks = chunk_messages(content) if a.type == "chat" else chunk_prose(content)
    chunk_ids = index_chunks(db, artifact_id, body.commit_ref, chunks)
    return {"chunk_ids": chunk_ids}


@router.post("/chunks/{chunk_id}/provenance")
def add_provenance_route(chunk_id: str, body: ProvenanceRequest, db: Session = Depends(get_db)):
    add_provenance_edge(db, chunk_id, body.to_chunk_id, body.relation)
    return {"status": "ok"}


@router.get("/chunks/{chunk_id}/provenance")
def get_provenance_route(chunk_id: str, db: Session = Depends(get_db)):
    return {"chain": trace_provenance(db, chunk_id)}
