import uuid
from datetime import datetime
from typing import List

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Blob(Base):
    __tablename__ = "blobs"

    hash: Mapped[str] = mapped_column(String, primary_key=True)
    content: Mapped[str] = mapped_column(String)
    size: Mapped[int] = mapped_column(Integer)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)


class Commit(Base):
    __tablename__ = "commits"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String)
    parent_ids: Mapped[List[str]] = mapped_column(JSON)
    blob_hash: Mapped[str] = mapped_column(String)
    author: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    head_commit_id: Mapped[str] = mapped_column(String)


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String)
    commit_ref: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(String)
    embedding: Mapped[List[float]] = mapped_column(Vector(384))
    span: Mapped[str] = mapped_column(String)


class ProvenanceEdge(Base):
    __tablename__ = "provenance_edges"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    from_chunk_id: Mapped[str] = mapped_column(String)
    to_chunk_id: Mapped[str] = mapped_column(String)
    relation: Mapped[str] = mapped_column(String)


class MergeRequest(Base):
    __tablename__ = "merge_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String)
    source_branch: Mapped[str] = mapped_column(String)
    target_branch: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    base_commit_ref: Mapped[str] = mapped_column(String)


class LastSeen(Base):
    __tablename__ = "last_seen"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String, primary_key=True)
    commit_ref: Mapped[str] = mapped_column(String)
