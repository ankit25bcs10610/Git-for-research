import os

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_user
from app.artifacts import get_artifact
from app.crdt.snapshot_bridge import commit_snapshot

router = APIRouter()


class CommitSnapshotRequest(BaseModel):
    branch_name: str
    author: str


def _artifact_or_404(db: Session, artifact_id: str):
    try:
        return get_artifact(db, artifact_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="artifact not found")


@router.post("/artifacts/{artifact_id}/live/commit-snapshot")
def commit_live_snapshot_route(
    artifact_id: str, body: CommitSnapshotRequest, db: Session = Depends(get_db)
):
    _artifact_or_404(db, artifact_id)
    require_user(db, body.author)

    snapshot_url = os.environ.get("CRDT_SNAPSHOT_URL", "http://localhost:1235")
    room = f"{artifact_id}__{body.branch_name}"
    try:
        response = requests.get(f"{snapshot_url}/snapshot/{room}", timeout=5)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"could not reach CRDT relay: {exc}")

    snapshot_text = response.json()["text"]
    commit_ref = commit_snapshot(db, artifact_id, body.branch_name, snapshot_text, body.author)
    return {"commit_ref": commit_ref}
