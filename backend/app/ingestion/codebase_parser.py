import io
import zipfile
from typing import Dict

from app.ingestion.base import ParsedArtifact


def parse_codebase_zip(zip_bytes: bytes) -> ParsedArtifact:
    buffer = io.BytesIO(zip_bytes)
    files: Dict[str, str] = {}
    with zipfile.ZipFile(buffer) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            raw_bytes = archive.read(entry.filename)
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                continue
            files[entry.filename] = text
    return ParsedArtifact(artifact_type="codebase", name="codebase", content=files)
