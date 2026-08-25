import uuid

from fastapi.testclient import TestClient

from app.artifacts import create_artifact
from app.db.base import get_session
from app.main import app
from app.versioning.dag_store import create_blob, create_branch, create_commit

client = TestClient(app)


def test_graph_route_returns_commits_branches_and_merge_requests():
    with get_session() as session:
        artifact_id = create_artifact(session, str(uuid.uuid4()), "doc", "graph route fixture")
        blob_hash = create_blob(session, f"root content {uuid.uuid4()}")
        root_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=blob_hash,
            parent_ids=[],
            author="user-1",
            message="root",
        )
        child_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=blob_hash,
            parent_ids=[root_id],
            author="user-1",
            message="child",
        )
        create_branch(session, artifact_id=artifact_id, name="main", head_commit_id=child_id)

    response = client.get(f"/api/artifacts/{artifact_id}/graph")

    assert response.status_code == 200
    body = response.json()
    assert [c["id"] for c in body["commits"]] == [root_id, child_id]
    assert body["commits"][1]["parent_ids"] == [root_id]
    assert body["branches"] == [{"name": "main", "head_commit_id": child_id}]
    assert body["merge_requests"] == []


def test_graph_route_404s_for_unknown_artifact():
    response = client.get(f"/api/artifacts/{uuid.uuid4()}/graph")
    assert response.status_code == 404
