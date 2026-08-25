import io
import uuid
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.db.base import get_session
from app.main import app
from app.users import create_user

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolated_artifact_store(tmp_path, monkeypatch):
    monkeypatch.setattr("app.versioning.git_adapter.ARTIFACT_STORE_PATH", str(tmp_path))


def _zip_bytes(files: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for filename, content in files.items():
            archive.writestr(filename, content)
    return buffer.getvalue()


def _make_user() -> str:
    username = f"codebase-user-{uuid.uuid4().hex[:8]}"
    with get_session() as session:
        create_user(session, username)
    return username


def _ingest_codebase(author: str, files: dict, workspace_id: str = None) -> str:
    workspace_id = workspace_id or str(uuid.uuid4())
    response = client.post(
        f"/api/workspaces/{workspace_id}/artifacts/ingest/codebase",
        files={"file": ("repo.zip", _zip_bytes(files), "application/zip")},
        data={"author": author},
    )
    assert response.status_code == 200, response.text
    return response.json()["artifact_id"]


def test_ingest_codebase_creates_artifact_with_initial_commit_on_master():
    author = _make_user()

    response = client.post(
        f"/api/workspaces/{uuid.uuid4()}/artifacts/ingest/codebase",
        files={"file": ("repo.zip", _zip_bytes({"main.py": "def add(a, b):\n    return a + b\n"}), "application/zip")},
        data={"author": author},
    )

    assert response.status_code == 200
    body = response.json()
    assert "artifact_id" in body
    assert "commit_ref" in body

    branches = client.get(f"/api/artifacts/{body['artifact_id']}/codebase/branches")
    assert branches.status_code == 200
    assert branches.json() == [{"name": "master", "head_commit_id": body["commit_ref"]}]


def test_ingest_codebase_rejects_unknown_author():
    response = client.post(
        f"/api/workspaces/{uuid.uuid4()}/artifacts/ingest/codebase",
        files={"file": ("repo.zip", _zip_bytes({"main.py": "x = 1\n"}), "application/zip")},
        data={"author": f"nobody-{uuid.uuid4()}"},
    )
    assert response.status_code == 404


def test_create_branch_and_commit_then_read_content():
    author = _make_user()
    artifact_id = _ingest_codebase(author, {"main.py": "x = 1\n"})

    branch_response = client.post(
        f"/api/artifacts/{artifact_id}/codebase/branches",
        json={"name": "feature", "from_ref": "master"},
    )
    assert branch_response.status_code == 200

    commit_response = client.post(
        f"/api/artifacts/{artifact_id}/codebase/commits",
        json={
            "branch_name": "feature",
            "files": {"main.py": "x = 2\n"},
            "message": "bump x",
            "author": author,
        },
    )
    assert commit_response.status_code == 200
    commit_ref = commit_response.json()["commit_ref"]

    content_response = client.get(f"/api/artifacts/{artifact_id}/codebase/content", params={"ref": commit_ref})
    assert content_response.status_code == 200
    assert content_response.json()["files"] == {"main.py": "x = 2\n"}


def test_diff_route_reports_file_level_changes():
    # GitVersionedArtifact.commit()'s `files` dict is an additive overlay
    # (it writes/overwrites paths given, it does not delete tracked paths
    # missing from the dict -- see test_git_adapter.py), so only add/modify
    # are exercised here via the HTTP route; deletion isn't exposed by this
    # commit contract.
    author = _make_user()
    artifact_id = _ingest_codebase(author, {"a.txt": "a\n", "b.txt": "b\n"})
    root_commit = client.get(f"/api/artifacts/{artifact_id}/codebase/branches").json()[0]["head_commit_id"]

    commit_response = client.post(
        f"/api/artifacts/{artifact_id}/codebase/commits",
        json={
            "branch_name": "master",
            "files": {"a.txt": "a changed\n", "c.txt": "new file\n"},
            "message": "modify a, add c",
            "author": author,
        },
    )
    new_commit = commit_response.json()["commit_ref"]

    diff_response = client.get(
        f"/api/artifacts/{artifact_id}/codebase/diff",
        params={"ref_a": root_commit, "ref_b": new_commit},
    )
    assert diff_response.status_code == 200
    changes = {c["path"]: c["status"] for c in diff_response.json()["changes"]}
    assert changes == {"a.txt": "modified", "c.txt": "added"}


def test_merge_request_lifecycle_clean_merge():
    author = _make_user()
    artifact_id = _ingest_codebase(author, {"a.txt": "a\n", "b.txt": "b\n"})

    client.post(f"/api/artifacts/{artifact_id}/codebase/branches", json={"name": "feature", "from_ref": "master"})
    client.post(
        f"/api/artifacts/{artifact_id}/codebase/commits",
        json={"branch_name": "feature", "files": {"a.txt": "a edited\n"}, "message": "edit a", "author": author},
    )
    client.post(
        f"/api/artifacts/{artifact_id}/codebase/commits",
        json={"branch_name": "master", "files": {"b.txt": "b edited\n"}, "message": "edit b", "author": author},
    )

    mr_response = client.post(
        f"/api/artifacts/{artifact_id}/codebase/merge-requests",
        json={"source_branch": "feature", "target_branch": "master", "author": author},
    )
    assert mr_response.status_code == 200
    mr_id = mr_response.json()["merge_request_id"]

    diff_response = client.get(f"/api/codebase/merge-requests/{mr_id}/diff")
    assert diff_response.status_code == 200
    assert diff_response.json()["has_conflict"] is False

    merge_response = client.post(f"/api/codebase/merge-requests/{mr_id}/merge", json={"resolutions": None, "author": author})
    assert merge_response.status_code == 200
    assert merge_response.json()["merged"] is True

    merge_requests = client.get(f"/api/artifacts/{artifact_id}/codebase/merge-requests").json()
    assert merge_requests[0]["status"] == "merged"
    assert merge_requests[0]["opened_by"] == author
    assert merge_requests[0]["merged_by"] == author


def test_merge_request_lifecycle_conflict_then_resolve():
    author = _make_user()
    artifact_id = _ingest_codebase(author, {"a.txt": "a\n"})

    client.post(f"/api/artifacts/{artifact_id}/codebase/branches", json={"name": "feature", "from_ref": "master"})
    client.post(
        f"/api/artifacts/{artifact_id}/codebase/commits",
        json={"branch_name": "feature", "files": {"a.txt": "feature version\n"}, "message": "edit", "author": author},
    )
    client.post(
        f"/api/artifacts/{artifact_id}/codebase/commits",
        json={"branch_name": "master", "files": {"a.txt": "master version\n"}, "message": "edit", "author": author},
    )

    mr_id = client.post(
        f"/api/artifacts/{artifact_id}/codebase/merge-requests",
        json={"source_branch": "feature", "target_branch": "master", "author": author},
    ).json()["merge_request_id"]

    diff_response = client.get(f"/api/codebase/merge-requests/{mr_id}/diff")
    assert diff_response.json()["has_conflict"] is True
    conflict_path = diff_response.json()["conflicts"][0]["path"]

    blocked = client.post(f"/api/codebase/merge-requests/{mr_id}/merge", json={"resolutions": None, "author": author})
    assert blocked.status_code == 409

    resolved = client.post(
        f"/api/codebase/merge-requests/{mr_id}/merge",
        json={"resolutions": {conflict_path: "resolved content\n"}, "author": author},
    )
    assert resolved.status_code == 200
    assert resolved.json()["merged"] is True

    content = client.get(
        f"/api/artifacts/{artifact_id}/codebase/content",
        params={"ref": "master"},
    ).json()
    assert content["files"]["a.txt"] == "resolved content\n"


def test_reject_merge_request():
    author = _make_user()
    artifact_id = _ingest_codebase(author, {"a.txt": "a\n"})
    client.post(f"/api/artifacts/{artifact_id}/codebase/branches", json={"name": "feature", "from_ref": "master"})

    mr_id = client.post(
        f"/api/artifacts/{artifact_id}/codebase/merge-requests",
        json={"source_branch": "feature", "target_branch": "master", "author": author},
    ).json()["merge_request_id"]

    reject_response = client.post(f"/api/codebase/merge-requests/{mr_id}/reject", json={"author": author})
    assert reject_response.status_code == 200

    merge_requests = client.get(f"/api/artifacts/{artifact_id}/codebase/merge-requests").json()
    assert merge_requests[0]["status"] == "rejected"
    assert merge_requests[0]["rejected_by"] == author
