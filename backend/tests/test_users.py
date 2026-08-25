import uuid

import pytest

from app.db.base import get_session
from app.users import create_user, get_user_by_username, list_users


def test_create_user_and_get_by_username():
    username = f"researcher-{uuid.uuid4()}"

    with get_session() as session:
        user_id = create_user(session, username, display_name="Ada Researcher")

        fetched = get_user_by_username(session, username)

        assert fetched.id == user_id
        assert fetched.username == username
        assert fetched.display_name == "Ada Researcher"


def test_create_user_defaults_display_name_to_username():
    username = f"researcher-{uuid.uuid4()}"

    with get_session() as session:
        create_user(session, username)

        fetched = get_user_by_username(session, username)

        assert fetched.display_name == username


def test_create_user_rejects_duplicate_username():
    username = f"researcher-{uuid.uuid4()}"

    with get_session() as session:
        create_user(session, username)

        with pytest.raises(ValueError):
            create_user(session, username)


def test_get_user_by_username_raises_for_unknown_username():
    with get_session() as session:
        with pytest.raises(ValueError):
            get_user_by_username(session, f"nobody-{uuid.uuid4()}")


def test_list_users_includes_created_user():
    username = f"researcher-{uuid.uuid4()}"

    with get_session() as session:
        create_user(session, username)

        usernames = [u.username for u in list_users(session)]

        assert username in usernames
