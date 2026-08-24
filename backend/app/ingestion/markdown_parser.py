from app.ingestion.base import ParsedArtifact


def parse_markdown(file_bytes: bytes, filename: str) -> ParsedArtifact:
    text = file_bytes.decode("utf-8")
    return ParsedArtifact(artifact_type="doc", name=filename, content=text)
