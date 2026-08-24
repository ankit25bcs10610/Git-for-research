import hashlib
import uuid
from datetime import datetime, timezone

from app.db.models import Blob, Branch, Commit


def create_blob(session, content: str) -> str:
    blob_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    existing = session.get(Blob, blob_hash)
    if existing is None:
        blob = Blob(hash=blob_hash, content=content, size=len(content.encode("utf-8")))
        session.add(blob)
        session.commit()
    return blob_hash


def get_blob_content(session, blob_hash: str) -> str:
    blob = session.get(Blob, blob_hash)
    if blob is None:
        raise ValueError(f"blob not found for hash {blob_hash}")
    return blob.content


def create_commit(
    session,
    artifact_id: str,
    blob_hash: str,
    parent_ids: list,
    author: str,
    message: str,
) -> str:
    commit_id = str(uuid.uuid4())
    commit = Commit(
        id=commit_id,
        artifact_id=artifact_id,
        parent_ids=parent_ids,
        blob_hash=blob_hash,
        author=author,
        message=message,
        created_at=datetime.now(timezone.utc),
    )
    session.add(commit)
    session.commit()
    return commit_id


def get_commit(session, commit_id: str) -> Commit:
    commit = session.get(Commit, commit_id)
    if commit is None:
        raise ValueError(f"commit not found for id {commit_id}")
    return commit


def create_branch(session, artifact_id: str, name: str, head_commit_id: str) -> None:
    branch = Branch(
        id=str(uuid.uuid4()),
        artifact_id=artifact_id,
        name=name,
        head_commit_id=head_commit_id,
    )
    session.add(branch)
    session.commit()


def get_branch_head(session, artifact_id: str, name: str) -> str:
    branch = (
        session.query(Branch)
        .filter_by(artifact_id=artifact_id, name=name)
        .one_or_none()
    )
    if branch is None:
        return None
    return branch.head_commit_id


def update_branch_head(session, artifact_id: str, name: str, new_commit_id: str) -> None:
    branch = (
        session.query(Branch)
        .filter_by(artifact_id=artifact_id, name=name)
        .one_or_none()
    )
    if branch is None:
        raise ValueError(f"branch '{name}' not found for artifact {artifact_id}")
    branch.head_commit_id = new_commit_id
    session.commit()
