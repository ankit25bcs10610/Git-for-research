import json
from pathlib import Path

from app.ingestion.base import ParsedArtifact
from app.ingestion.claude_parser import parse_claude_export

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_parse_claude_export_maps_roles_and_preserves_order():
    fixture_path = FIXTURES_DIR / "claude_conversations.json"
    json_bytes = fixture_path.read_bytes()

    artifacts = parse_claude_export(json_bytes)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert isinstance(artifact, ParsedArtifact)
    assert artifact.artifact_type == "chat"
    assert artifact.name == "Debugging a Python script"

    messages = json.loads(artifact.content)
    assert messages == [
        {
            "role": "user",
            "text": "Why does my script raise a KeyError?",
            "ts": "2026-01-01T10:00:00Z",
        },
        {
            "role": "assistant",
            "text": "A KeyError means the dictionary key you accessed does not exist.",
            "ts": "2026-01-01T10:00:05Z",
        },
        {
            "role": "user",
            "text": "Got it, thanks!",
            "ts": "2026-01-01T10:00:12Z",
        },
    ]
