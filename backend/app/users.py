import uuid
from datetime import datetime, timezone

from app.db.models import User


def create_user(session, username: str, display_name: str = None) -> str:
    existing = session.query(User).filter_by(username=username).one_or_none()
    if existing is not None:
        raise ValueError(f"username '{username}' already exists")

    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        username=username,
        display_name=display_name or username,
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)
    session.commit()
    return user_id


def get_user_by_username(session, username: str) -> User:
    user = session.query(User).filter_by(username=username).one_or_none()
    if user is None:
        raise ValueError(f"user not found for username {username}")
    return user


def list_users(session) -> list:
    return session.query(User).order_by(User.created_at).all()
