import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

from fastapi.testclient import TestClient

from app.db.base import get_session
from app.main import app
from app.retrieval.query import index_chunks

client = TestClient(app)


class _FakeGroqHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self.send_response(self.server.status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if self.server.status_code == 200:
            body = {"choices": [{"message": {"content": self.server.answer_text}}]}
        else:
            body = {"error": "boom"}
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, *args):
        pass


def _start_fake_groq(answer_text: str = "", status_code: int = 200) -> HTTPServer:
    server = HTTPServer(("127.0.0.1", 0), _FakeGroqHandler)
    server.answer_text = answer_text
    server.status_code = status_code
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _index_a_findable_chunk() -> str:
    artifact_id = str(uuid.uuid4())
    commit_ref = str(uuid.uuid4())
    marker = f"unique-marker-{uuid.uuid4()}"
    with get_session() as session:
        index_chunks(session, artifact_id, commit_ref, [f"The answer is {marker}."])
    return marker


def test_search_answer_route_returns_501_when_groq_api_key_not_set(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    response = client.get("/api/search/answer", params={"q": "anything"})

    assert response.status_code == 501


def test_search_answer_route_returns_synthesized_answer_and_sources(monkeypatch):
    marker = _index_a_findable_chunk()
    fake_groq = _start_fake_groq(answer_text=f"The answer mentions {marker}. [1]")
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    monkeypatch.setenv("GROQ_API_URL", f"http://127.0.0.1:{fake_groq.server_port}")

    response = client.get("/api/search/answer", params={"q": marker, "top_k": 3})

    assert response.status_code == 200
    body = response.json()
    assert marker in body["answer"]
    assert len(body["sources"]) > 0
    assert any(marker in s["text"] for s in body["sources"])

    fake_groq.shutdown()


def test_search_answer_route_returns_502_when_groq_unreachable(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    monkeypatch.setenv("GROQ_API_URL", "http://127.0.0.1:1")

    response = client.get("/api/search/answer", params={"q": "anything"})

    assert response.status_code == 502


def test_search_answer_route_returns_502_when_groq_errors(monkeypatch):
    fake_groq = _start_fake_groq(status_code=500)
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    monkeypatch.setenv("GROQ_API_URL", f"http://127.0.0.1:{fake_groq.server_port}")

    response = client.get("/api/search/answer", params={"q": "anything"})

    assert response.status_code == 502
    fake_groq.shutdown()
