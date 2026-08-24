import hashlib

from app.db.models import Blob


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
