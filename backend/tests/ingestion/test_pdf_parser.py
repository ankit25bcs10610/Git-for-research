import json
from pathlib import Path

from app.ingestion.base import ParsedArtifact
from app.ingestion.pdf_parser import parse_pdf

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_parse_pdf_extracts_text_per_page():
    fixture_path = FIXTURES_DIR / "sample.pdf"
    file_bytes = fixture_path.read_bytes()

    result = parse_pdf(file_bytes, "sample.pdf")

    assert isinstance(result, ParsedArtifact)
    assert result.artifact_type == "pdf"
    assert result.name == "sample.pdf"

    pages = json.loads(result.content)
    assert len(pages) == 2
    assert pages[0]["page"] == 1
    assert pages[0]["text"].strip() == "Page one content."
    assert pages[1]["page"] == 2
    assert pages[1]["text"].strip() == "Page two content."
