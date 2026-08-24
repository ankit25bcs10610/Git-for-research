from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.collab.agent_editor import agent_edit
from app.collab.merge_requests import (
    create_merge_request,
    get_merge_request_diff,
    merge_merge_request,
    reject_merge_request,
)

router = APIRouter()


class MergeRequestCreate(BaseModel):
    source_branch: str
    target_branch: str


class MergeRequestResolve(BaseModel):
    resolutions: dict[int, str] | None = None


class AgentEditRequest(BaseModel):
    base_branch: str
    instruction: str
    proposed_content: str


@router.post("/artifacts/{artifact_id}/merge-requests")
def create_merge_request_route(artifact_id: str, body: MergeRequestCreate, db: Session = Depends(get_db)):
    mr_id = create_merge_request(db, artifact_id, body.source_branch, body.target_branch)
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
    merged = merge_merge_request(db, mr_id, body.resolutions)
    if not merged:
        raise HTTPException(status_code=409, detail="merge blocked: unresolved conflicts, wrong resolutions, already closed, or the target branch advanced")
    return {"merged": True}


@router.post("/merge-requests/{mr_id}/reject")
def reject_route(mr_id: str, db: Session = Depends(get_db)):
    reject_merge_request(db, mr_id)
    return {"status": "rejected"}


@router.post("/artifacts/{artifact_id}/agent-edit")
def agent_edit_route(artifact_id: str, body: AgentEditRequest, db: Session = Depends(get_db)):
    # No hosted LLM call happens in this backend (matches the "no external
    # LLM dependency" constraint): the caller supplies the proposed content
    # directly -- that caller is expected to be a script/agent that already
    # generated it (e.g. by calling a real LLM API of its own choosing).
    def caller_supplied_content(_instruction: str, _current_content: str) -> str:
        return body.proposed_content

    mr_id = agent_edit(db, artifact_id, body.base_branch, body.instruction, caller_supplied_content)
    return {"merge_request_id": mr_id}
