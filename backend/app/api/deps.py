from app.db.base import get_session
from app.versioning.diff_engine import tokenize_messages, tokenize_paragraphs


def get_db():
    with get_session() as session:
        yield session


def tokenizer_for_type(artifact_type: str):
    if artifact_type == "chat":
        return tokenize_messages
    return tokenize_paragraphs
