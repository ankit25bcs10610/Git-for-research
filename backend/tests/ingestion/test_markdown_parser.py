from pathlib import Path

from app.ingestion.base import ParsedArtifact
from app.ingestion.markdown_parser import parse_markdown

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_parse_markdown_returns_parsed_artifact():
    fixture_path = FIXTURES_DIR / "sample.md"
    file_bytes = fixture_path.read_bytes()
    expected_text = fixture_path.read_text(encoding="utf-8")

    result = parse_markdown(file_bytes, "sample.md")

    assert isinstance(result, ParsedArtifact)
    assert result.artifact_type == "doc"
    assert result.name == "sample.md"
    assert result.content == expected_text
