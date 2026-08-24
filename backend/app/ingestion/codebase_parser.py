import io
import os
import zipfile
from typing import Dict, Iterable

from app.ingestion.base import ParsedArtifact
from app.versioning.git_adapter import clone_repo


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


def parse_codebase_git(repo_path_or_url: str, dest_path: str) -> ParsedArtifact:
    clone_repo(repo_path_or_url, dest_path)
    # Full history is preserved separately because dest_path is the git
    # repository later opened by GitVersionedArtifact; this ParsedArtifact
    # content field is only a snapshot used for chunking and retrieval.
    files: Dict[str, str] = {}
    for root, dirs, filenames in os.walk(dest_path):
        if ".git" in dirs:
            dirs.remove(".git")
        for filename in filenames:
            full_path = os.path.join(root, filename)
            if os.path.islink(full_path):
                # Skip symlinks: a cloned repo is untrusted input, and a
                # symlink could point outside dest_path (e.g. /etc/passwd,
                # an SSH key). Following it would leak arbitrary files from
                # the host into the ingested artifact content.
                continue
            relative_path = os.path.relpath(full_path, dest_path).replace(os.sep, "/")
            try:
                # O_NOFOLLOW makes this TOCTOU-safe: even if a symlink is
                # swapped in between the islink() check above and this open,
                # the OS refuses to follow it and raises OSError instead.
                fd = os.open(full_path, os.O_RDONLY | os.O_NOFOLLOW)
            except OSError:
                continue
            with os.fdopen(fd, "rb") as handle:
                raw_bytes = handle.read()
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                continue
            files[relative_path] = text
    name = os.path.basename(os.path.normpath(dest_path))
    return ParsedArtifact(artifact_type="codebase", name=name, content=files)
