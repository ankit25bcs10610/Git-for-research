from fastapi import HTTPException

from app.db.base import get_session
from app.users import get_user_by_username
from app.versioning.diff_engine import tokenizer_for_type


def get_db():
    with get_session() as session:
        yield session


def require_user(db, username: str):
    try:
        return get_user_by_username(db, username)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"user '{username}' not found")
