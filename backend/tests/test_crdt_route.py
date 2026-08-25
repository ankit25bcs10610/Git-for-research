import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

from fastapi.testclient import TestClient

from app.artifacts import create_artifact
from app.db.base import get_session
from app.main import app
from app.users import create_user
from app.versioning.dag_store import get_branch_head, get_commit

client = TestClient(app)


class _FakeSnapshotHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"text": self.server.snapshot_text}).encode())

    def log_message(self, *args):
        pass


def _start_fake_relay(snapshot_text: str) -> HTTPServer:
    server = HTTPServer(("127.0.0.1", 0), _FakeSnapshotHandler)
    server.snapshot_text = snapshot_text
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_commit_live_snapshot_route_creates_a_real_commit(monkeypatch):
    with get_session() as session:
        artifact_id = create_artifact(session, str(uuid.uuid4()), "doc", "live-edit fixture")
        username = f"researcher-{uuid.uuid4()}"
        create_user(session, username)

    fake_relay = _start_fake_relay("Live paragraph one.")
    monkeypatch.setenv("CRDT_SNAPSHOT_URL", f"http://127.0.0.1:{fake_relay.server_port}")

    response = client.post(
        f"/api/artifacts/{artifact_id}/live/commit-snapshot",
        json={"branch_name": "main", "author": username},
    )

    assert response.status_code == 200
    commit_ref = response.json()["commit_ref"]

    with get_session() as session:
        assert get_branch_head(session, artifact_id, "main") == commit_ref
        commit = get_commit(session, commit_ref)
        assert commit.message == "Live edit snapshot"
        assert commit.author == username

    fake_relay.shutdown()


def test_commit_live_snapshot_route_rejects_unknown_author(monkeypatch):
    with get_session() as session:
        artifact_id = create_artifact(session, str(uuid.uuid4()), "doc", "live-edit fixture")

    fake_relay = _start_fake_relay("irrelevant")
    monkeypatch.setenv("CRDT_SNAPSHOT_URL", f"http://127.0.0.1:{fake_relay.server_port}")

    response = client.post(
        f"/api/artifacts/{artifact_id}/live/commit-snapshot",
        json={"branch_name": "main", "author": f"nobody-{uuid.uuid4()}"},
    )

    assert response.status_code == 404
    fake_relay.shutdown()


def test_commit_live_snapshot_route_404s_for_unknown_artifact():
    response = client.post(
        f"/api/artifacts/{uuid.uuid4()}/live/commit-snapshot",
        json={"branch_name": "main", "author": "irrelevant"},
    )
    assert response.status_code == 404


def test_commit_live_snapshot_route_502s_when_relay_unreachable(monkeypatch):
    with get_session() as session:
        artifact_id = create_artifact(session, str(uuid.uuid4()), "doc", "live-edit fixture")
        username = f"researcher-{uuid.uuid4()}"
        create_user(session, username)

    # Port 1 is a reserved/unused port that will refuse the connection.
    monkeypatch.setenv("CRDT_SNAPSHOT_URL", "http://127.0.0.1:1")

    response = client.post(
        f"/api/artifacts/{artifact_id}/live/commit-snapshot",
        json={"branch_name": "main", "author": username},
    )

    assert response.status_code == 502
