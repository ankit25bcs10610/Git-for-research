import json
from pathlib import Path

from app.ingestion.base import ParsedArtifact
from app.ingestion.chatgpt_parser import parse_chatgpt_export

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_parse_chatgpt_export_follows_current_branch_only():
    fixture_path = FIXTURES_DIR / "chatgpt_conversations.json"
    json_bytes = fixture_path.read_bytes()

    artifacts = parse_chatgpt_export(json_bytes)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert isinstance(artifact, ParsedArtifact)
    assert artifact.artifact_type == "chat"
    assert artifact.name == "Reversing a string"

    messages = json.loads(artifact.content)
    assert messages == [
        {"role": "user", "text": "How do I reverse a string in Python?", "ts": 1000.0},
        {"role": "assistant", "text": "You can use s[::-1] to reverse a string.", "ts": 1002.0},
        {"role": "user", "text": "Great, thanks!", "ts": 1003.0},
    ]
    texts = [message["text"] for message in messages]
    assert "Use reversed(s)." not in texts
