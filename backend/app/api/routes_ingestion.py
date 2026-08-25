import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_user, tokenizer_for_type
from app.artifacts import create_artifact
from app.ingestion.chatgpt_parser import parse_chatgpt_export
from app.ingestion.claude_parser import parse_claude_export
from app.ingestion.markdown_parser import parse_markdown
from app.ingestion.pdf_parser import parse_pdf
from app.retrieval.chunker import chunk_messages, chunk_prose
from app.retrieval.query import index_chunks
from app.versioning.dag_adapter import DagVersionedArtifact

router = APIRouter()


def _commit_and_index(session: Session, artifact_id: str, artifact_type: str, content: str, author: str) -> str:
    artifact = DagVersionedArtifact(session, artifact_id, tokenizer_for_type(artifact_type))
    commit_ref = artifact.commit(content, author, "initial import", None)
    artifact.branch("main", commit_ref)

    chunks = chunk_messages(content) if artifact_type == "chat" else chunk_prose(content)
    index_chunks(session, artifact_id, commit_ref, chunks)
    return commit_ref


@router.post("/workspaces/{workspace_id}/artifacts/ingest/markdown")
async def ingest_markdown(
    workspace_id: str, file: UploadFile = File(...), author: str = Form(...), db: Session = Depends(get_db)
):
    require_user(db, author)
    raw = await file.read()
    parsed = parse_markdown(raw, file.filename or "untitled.md")
    artifact_id = create_artifact(db, workspace_id, parsed.artifact_type, parsed.name)
    commit_ref = _commit_and_index(db, artifact_id, parsed.artifact_type, parsed.content, author)
    return {"artifact_id": artifact_id, "commit_ref": commit_ref}


@router.post("/workspaces/{workspace_id}/artifacts/ingest/chatgpt")
async def ingest_chatgpt(
    workspace_id: str, file: UploadFile = File(...), author: str = Form(...), db: Session = Depends(get_db)
):
    require_user(db, author)
    raw = await file.read()
    try:
        parsed_list = parse_chatgpt_export(raw)
    except (KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid ChatGPT export: {exc}")

    results = []
    for parsed in parsed_list:
        artifact_id = create_artifact(db, workspace_id, parsed.artifact_type, parsed.name)
        commit_ref = _commit_and_index(db, artifact_id, parsed.artifact_type, parsed.content, author)
        results.append({"artifact_id": artifact_id, "commit_ref": commit_ref, "name": parsed.name})
    return {"artifacts": results}


@router.post("/workspaces/{workspace_id}/artifacts/ingest/claude")
async def ingest_claude(
    workspace_id: str, file: UploadFile = File(...), author: str = Form(...), db: Session = Depends(get_db)
):
    require_user(db, author)
    raw = await file.read()
    try:
        parsed_list = parse_claude_export(raw)
    except (KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid Claude export: {exc}")

    results = []
    for parsed in parsed_list:
        artifact_id = create_artifact(db, workspace_id, parsed.artifact_type, parsed.name)
        commit_ref = _commit_and_index(db, artifact_id, parsed.artifact_type, parsed.content, author)
        results.append({"artifact_id": artifact_id, "commit_ref": commit_ref, "name": parsed.name})
    return {"artifacts": results}


@router.post("/workspaces/{workspace_id}/artifacts/ingest/pdf")
async def ingest_pdf(
    workspace_id: str, file: UploadFile = File(...), author: str = Form(...), db: Session = Depends(get_db)
):
    require_user(db, author)
    raw = await file.read()
    parsed = parse_pdf(raw, file.filename or "untitled.pdf")

    # parse_pdf's content is a JSON array of {"page": n, "text": ...} objects,
    # which has no blank lines for tokenize_paragraphs to split on. Join the
    # page texts with a blank line so the committed content is real,
    # paragraph-diffable prose instead of an opaque JSON blob.
    pages = json.loads(parsed.content)
    joined_content = "\n\n".join(page["text"] for page in pages if page.get("text"))

    artifact_id = create_artifact(db, workspace_id, parsed.artifact_type, parsed.name)
    commit_ref = _commit_and_index(db, artifact_id, parsed.artifact_type, joined_content, author)
    return {"artifact_id": artifact_id, "commit_ref": commit_ref}
