from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_user
from app.collab.agent_editor import agent_edit
from app.collab.merge_requests import (
    create_merge_request,
    get_merge_request_diff,
    merge_merge_request,
    reject_merge_request,
)
from app.db.models import MergeRequest

router = APIRouter()


class MergeRequestCreate(BaseModel):
    source_branch: str
    target_branch: str
    author: str


class MergeRequestResolve(BaseModel):
    resolutions: dict[int, str] | None = None
    author: str


class MergeRequestReject(BaseModel):
    author: str


class AgentEditRequest(BaseModel):
    base_branch: str
    instruction: str
    proposed_content: str
    author: str


@router.get("/artifacts/{artifact_id}/merge-requests")
def list_merge_requests_route(artifact_id: str, db: Session = Depends(get_db)):
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


@router.post("/artifacts/{artifact_id}/merge-requests")
def create_merge_request_route(artifact_id: str, body: MergeRequestCreate, db: Session = Depends(get_db)):
    require_user(db, body.author)
    mr_id = create_merge_request(db, artifact_id, body.source_branch, body.target_branch, body.author)
    return {"merge_request_id": mr_id}


@router.get("/merge-requests/{mr_id}/diff")
def get_merge_request_diff_route(mr_id: str, db: Session = Depends(get_db)):
    result = get_merge_request_diff(db, mr_id)
    return {
        "merged_tokens": result["merged_tokens"],
        "conflicts": result["conflicts"],
        "has_conflict": len(result["conflicts"]) > 0,
    }


@router.post("/merge-requests/{mr_id}/merge")
def merge_route(mr_id: str, body: MergeRequestResolve, db: Session = Depends(get_db)):
    require_user(db, body.author)
    merged = merge_merge_request(db, mr_id, body.resolutions, body.author)
    if not merged:
        raise HTTPException(status_code=409, detail="merge blocked: unresolved conflicts, wrong resolutions, already closed, or the target branch advanced")
    return {"merged": True}


@router.post("/merge-requests/{mr_id}/reject")
def reject_route(mr_id: str, body: MergeRequestReject, db: Session = Depends(get_db)):
    require_user(db, body.author)
    reject_merge_request(db, mr_id, body.author)
    return {"status": "rejected"}


@router.post("/artifacts/{artifact_id}/agent-edit")
def agent_edit_route(artifact_id: str, body: AgentEditRequest, db: Session = Depends(get_db)):
    require_user(db, body.author)

    # No hosted LLM call happens in this backend (matches the "no external
    # LLM dependency" constraint): the caller supplies the proposed content
    # directly -- that caller is expected to be a script/agent that already
    # generated it (e.g. by calling a real LLM API of its own choosing).
    def caller_supplied_content(_instruction: str, _current_content: str) -> str:
        return body.proposed_content

    mr_id = agent_edit(db, artifact_id, body.base_branch, body.instruction, caller_supplied_content, body.author)
    return {"merge_request_id": mr_id}
