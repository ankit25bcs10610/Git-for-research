import io
import zipfile
from typing import Dict, Iterable

from app.ingestion.base import ParsedArtifact


def _derive_top_level_name(paths: Iterable[str], fallback: str = "codebase") -> str:
    top_levels = set()
    for path in paths:
        normalized = path.replace("\\", "/")
        parts = normalized.split("/")
        if len(parts) > 1 and parts[0]:
            top_levels.add(parts[0])
    if len(top_levels) == 1:
        return top_levels.pop()
    return fallback


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
        name = _derive_top_level_name(archive.namelist())
    return ParsedArtifact(artifact_type="codebase", name=name, content=files)
