import uuid

from fastapi.testclient import TestClient

from app.artifacts import create_artifact
from app.db.base import get_session
from app.main import app
from app.users import create_user
from app.versioning.dag_store import create_blob, create_branch, create_commit

client = TestClient(app)


def _make_artifact_with_main_branch():
    with get_session() as session:
        artifact_id = create_artifact(session, str(uuid.uuid4()), "doc", "identity fixture")
        blob_hash = create_blob(session, f"root content {uuid.uuid4()}")
        root_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=blob_hash,
            parent_ids=[],
            author="seed-author",
            message="root",
        )
        create_branch(session, artifact_id=artifact_id, name="main", head_commit_id=root_id)
    return artifact_id


def test_commit_route_rejects_unknown_author():
    artifact_id = _make_artifact_with_main_branch()

    response = client.post(
        f"/api/artifacts/{artifact_id}/commits",
        json={
            "branch_name": "main",
            "content": "new content",
            "message": "edit",
            "author": f"nobody-{uuid.uuid4()}",
        },
    )

    assert response.status_code == 404


def test_commit_route_accepts_known_author():
    artifact_id = _make_artifact_with_main_branch()
    username = f"researcher-{uuid.uuid4()}"
    with get_session() as session:
        create_user(session, username)

    response = client.post(
        f"/api/artifacts/{artifact_id}/commits",
        json={"branch_name": "main", "content": "new content", "message": "edit", "author": username},
    )

    assert response.status_code == 200


def test_mark_seen_route_rejects_unknown_user():
    artifact_id = _make_artifact_with_main_branch()

    response = client.post(
        f"/api/artifacts/{artifact_id}/seen",
        json={"user_id": f"nobody-{uuid.uuid4()}", "commit_ref": "irrelevant"},
    )

    assert response.status_code == 404


def test_changes_route_rejects_unknown_user():
    artifact_id = _make_artifact_with_main_branch()

    response = client.get(
        f"/api/artifacts/{artifact_id}/changes",
        params={"user_id": f"nobody-{uuid.uuid4()}", "branch_name": "main"},
    )

    assert response.status_code == 404
