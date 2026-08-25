from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_user
from app.artifacts import get_artifact
from app.collab.codebase_merge_requests import (
    create_merge_request,
    get_merge_request_diff,
    merge_merge_request,
    reject_merge_request,
)
from app.db.models import MergeRequest
from app.retrieval.chunker import chunk_code
from app.retrieval.query import index_chunks
from app.versioning.git_adapter import GitVersionedArtifact, repo_path_for_artifact

router = APIRouter()


class CodebaseBranchRequest(BaseModel):
    name: str
    from_ref: str


class CodebaseCommitRequest(BaseModel):
    branch_name: str
    files: dict[str, str]
    message: str
    author: str


class CodebaseMergeRequestCreate(BaseModel):
    source_branch: str
    target_branch: str
    author: str


class CodebaseMergeRequestResolve(BaseModel):
    resolutions: dict[str, str] | None = None
    author: str


class CodebaseMergeRequestReject(BaseModel):
    author: str


def _codebase_artifact_or_404(db: Session, artifact_id: str) -> GitVersionedArtifact:
    try:
        a = get_artifact(db, artifact_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="artifact not found")
    if a.type != "codebase":
        raise HTTPException(status_code=400, detail="artifact is not a codebase artifact")
    return GitVersionedArtifact(repo_path_for_artifact(artifact_id))


def _codebase_merge_request_or_404(db: Session, mr_id: str) -> tuple[MergeRequest, GitVersionedArtifact]:
    mr = db.get(MergeRequest, mr_id)
    if mr is None:
        raise HTTPException(status_code=404, detail="merge request not found")
    return mr, GitVersionedArtifact(repo_path_for_artifact(mr.artifact_id))


@router.get("/artifacts/{artifact_id}/codebase/branches")
def list_codebase_branches_route(artifact_id: str, db: Session = Depends(get_db)):
    artifact = _codebase_artifact_or_404(db, artifact_id)
    return [{"name": name, "head_commit_id": artifact.branch_head(name)} for name in artifact.list_branches()]


@router.post("/artifacts/{artifact_id}/codebase/branches")
def create_codebase_branch_route(artifact_id: str, body: CodebaseBranchRequest, db: Session = Depends(get_db)):
    artifact = _codebase_artifact_or_404(db, artifact_id)
    try:
        artifact.branch(body.name, body.from_ref)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"name": body.name, "head_commit_id": artifact.branch_head(body.name)}


@router.post("/artifacts/{artifact_id}/codebase/commits")
def create_codebase_commit_route(artifact_id: str, body: CodebaseCommitRequest, db: Session = Depends(get_db)):
    require_user(db, body.author)
    artifact = _codebase_artifact_or_404(db, artifact_id)
    try:
        artifact.checkout_branch(body.branch_name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"branch '{body.branch_name}' not found")
    commit_ref = artifact.commit(body.files, body.author, body.message)

    index_chunks(db, artifact_id, commit_ref, chunk_code(artifact.get_content(commit_ref)))

    return {"commit_ref": commit_ref, "branch_name": body.branch_name}


@router.get("/artifacts/{artifact_id}/codebase/diff")
def get_codebase_diff_route(artifact_id: str, ref_a: str, ref_b: str, db: Session = Depends(get_db)):
    artifact = _codebase_artifact_or_404(db, artifact_id)
    return {"changes": artifact.diff(ref_a, ref_b)}


@router.get("/artifacts/{artifact_id}/codebase/content")
def get_codebase_content_route(artifact_id: str, ref: str, db: Session = Depends(get_db)):
    artifact = _codebase_artifact_or_404(db, artifact_id)
    return {"files": artifact.get_content(ref)}


@router.get("/artifacts/{artifact_id}/codebase/merge-requests")
def list_codebase_merge_requests_route(artifact_id: str, db: Session = Depends(get_db)):
    rows = db.query(MergeRequest).filter_by(artifact_id=artifact_id).all()
    return [
        {
            "id": mr.id,
            "source_branch": mr.source_branch,
            "target_branch": mr.target_branch,
            "status": mr.status,
            "opened_by": mr.opened_by,
            "merged_by": mr.merged_by,
            "rejected_by": mr.rejected_by,
        }
        for mr in rows
    ]


@router.post("/artifacts/{artifact_id}/codebase/merge-requests")
def create_codebase_merge_request_route(
    artifact_id: str, body: CodebaseMergeRequestCreate, db: Session = Depends(get_db)
):
    require_user(db, body.author)
    artifact = _codebase_artifact_or_404(db, artifact_id)
    mr_id = create_merge_request(db, artifact, artifact_id, body.source_branch, body.target_branch, body.author)
    return {"merge_request_id": mr_id}


@router.get("/codebase/merge-requests/{mr_id}/diff")
def get_codebase_merge_request_diff_route(mr_id: str, db: Session = Depends(get_db)):
    mr, artifact = _codebase_merge_request_or_404(db, mr_id)
    result = get_merge_request_diff(db, artifact, mr_id)
    return {"conflicts": result["conflicts"], "has_conflict": len(result["conflicts"]) > 0}


@router.post("/codebase/merge-requests/{mr_id}/merge")
def merge_codebase_merge_request_route(
    mr_id: str, body: CodebaseMergeRequestResolve, db: Session = Depends(get_db)
):
    require_user(db, body.author)
    mr, artifact = _codebase_merge_request_or_404(db, mr_id)
    merged = merge_merge_request(db, artifact, mr_id, body.resolutions, body.author)
    if not merged:
        raise HTTPException(
            status_code=409,
            detail="merge blocked: unresolved conflicts, wrong resolutions, or already closed",
        )
    return {"merged": True}


@router.post("/codebase/merge-requests/{mr_id}/reject")
def reject_codebase_merge_request_route(
    mr_id: str, body: CodebaseMergeRequestReject, db: Session = Depends(get_db)
):
    require_user(db, body.author)
    reject_merge_request(db, mr_id, body.author)
    return {"status": "rejected"}
