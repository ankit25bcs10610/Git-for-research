from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_user, tokenizer_for_type
from app.artifacts import get_artifact, list_artifacts
from app.crdt.last_seen import get_changes_since, mark_seen
from app.db.models import Branch, MergeRequest
from app.retrieval.chunker import chunk_messages, chunk_prose
from app.retrieval.query import index_chunks
from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.dag_store import list_commits, update_branch_head

router = APIRouter()


class BranchRequest(BaseModel):
    name: str
    from_ref: str


class CommitRequest(BaseModel):
    branch_name: str
    content: str
    message: str
    author: str


class SeenRequest(BaseModel):
    user_id: str
    commit_ref: str


def _artifact_or_404(db: Session, artifact_id: str):
    try:
        return get_artifact(db, artifact_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="artifact not found")


@router.get("/workspaces/{workspace_id}/artifacts")
def get_workspace_artifacts(workspace_id: str, db: Session = Depends(get_db)):
    rows = list_artifacts(db, workspace_id)
    return [
        {"id": a.id, "workspaceId": a.workspace_id, "type": a.type, "name": a.name} for a in rows
    ]


@router.get("/artifacts/{artifact_id}")
def get_artifact_detail(artifact_id: str, db: Session = Depends(get_db)):
    a = _artifact_or_404(db, artifact_id)
    return {"id": a.id, "workspaceId": a.workspace_id, "type": a.type, "name": a.name}


@router.get("/artifacts/{artifact_id}/graph")
def get_artifact_graph_route(artifact_id: str, db: Session = Depends(get_db)):
    _artifact_or_404(db, artifact_id)
    commits = list_commits(db, artifact_id)
    branches = db.query(Branch).filter_by(artifact_id=artifact_id).all()
    merge_requests = db.query(MergeRequest).filter_by(artifact_id=artifact_id).all()
    return {
        "commits": [
            {
                "id": c.id,
                "parent_ids": c.parent_ids,
                "author": c.author,
                "message": c.message,
                "created_at": c.created_at.isoformat(),
            }
            for c in commits
        ],
        "branches": [{"name": b.name, "head_commit_id": b.head_commit_id} for b in branches],
        "merge_requests": [
            {
                "id": mr.id,
                "source_branch": mr.source_branch,
                "target_branch": mr.target_branch,
                "status": mr.status,
            }
            for mr in merge_requests
        ],
    }


@router.get("/artifacts/{artifact_id}/branches")
def list_branches_route(artifact_id: str, db: Session = Depends(get_db)):
    _artifact_or_404(db, artifact_id)
    rows = db.query(Branch).filter_by(artifact_id=artifact_id).all()
    return [{"name": b.name, "head_commit_id": b.head_commit_id} for b in rows]


@router.post("/artifacts/{artifact_id}/branches")
def create_branch_route(artifact_id: str, body: BranchRequest, db: Session = Depends(get_db)):
    a = _artifact_or_404(db, artifact_id)
    artifact = DagVersionedArtifact(db, artifact_id, tokenizer_for_type(a.type))
    try:
        artifact.branch(body.name, body.from_ref)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"name": body.name, "head_commit_id": artifact.branch_head(body.name)}


@router.post("/artifacts/{artifact_id}/commits")
def create_commit_route(artifact_id: str, body: CommitRequest, db: Session = Depends(get_db)):
    a = _artifact_or_404(db, artifact_id)
    require_user(db, body.author)
    artifact = DagVersionedArtifact(db, artifact_id, tokenizer_for_type(a.type))
    parent_ref = artifact.branch_head(body.branch_name)
    if parent_ref is None:
        raise HTTPException(status_code=404, detail=f"branch '{body.branch_name}' not found")

    commit_ref = artifact.commit(body.content, body.author, body.message, parent_ref)
    update_branch_head(db, artifact_id, body.branch_name, commit_ref)

    chunks = chunk_messages(body.content) if a.type == "chat" else chunk_prose(body.content)
    index_chunks(db, artifact_id, commit_ref, chunks)

    return {"commit_ref": commit_ref, "branch_name": body.branch_name}


@router.get("/artifacts/{artifact_id}/diff")
def get_diff_route(artifact_id: str, ref_a: str, ref_b: str, db: Session = Depends(get_db)):
    a = _artifact_or_404(db, artifact_id)
    artifact = DagVersionedArtifact(db, artifact_id, tokenizer_for_type(a.type))
    return {"entries": artifact.diff(ref_a, ref_b)}


@router.get("/artifacts/{artifact_id}/content")
def get_content_route(artifact_id: str, ref: str, db: Session = Depends(get_db)):
    a = _artifact_or_404(db, artifact_id)
    artifact = DagVersionedArtifact(db, artifact_id, tokenizer_for_type(a.type))
    return {"content": artifact.get_content(ref)}


@router.get("/artifacts/{artifact_id}/changes")
def get_changes_route(
    artifact_id: str, user_id: str, branch_name: str = "main", db: Session = Depends(get_db)
):
    _artifact_or_404(db, artifact_id)
    require_user(db, user_id)
    commits = get_changes_since(db, user_id, artifact_id, branch_name)
    return [
        {
            "id": c.id,
            "message": c.message,
            "author": c.author,
            "created_at": c.created_at.isoformat(),
        }
        for c in commits
    ]


@router.post("/artifacts/{artifact_id}/seen")
def mark_seen_route(artifact_id: str, body: SeenRequest, db: Session = Depends(get_db)):
    _artifact_or_404(db, artifact_id)
    require_user(db, body.user_id)
    mark_seen(db, body.user_id, artifact_id, body.commit_ref)
    return {"status": "ok"}
