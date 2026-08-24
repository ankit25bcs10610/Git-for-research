import io
import zipfile

from app.ingestion.codebase_parser import parse_codebase_zip


def _build_zip_bytes(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for filename, raw_bytes in entries.items():
            archive.writestr(filename, raw_bytes)
    return buffer.getvalue()


def test_parse_codebase_zip_extracts_text_and_skips_binary():
    zip_bytes = _build_zip_bytes(
        {
            "main.py": b"print('hello world')\n",
            "README.md": b"# Sample Project\n",
            "data.bin": b"\xff\xfe\x00\x01binary-garbage\x80\x81",
        }
    )

    artifact = parse_codebase_zip(zip_bytes)

    assert artifact.artifact_type == "codebase"
    assert artifact.name == "codebase"
    assert artifact.content == {
        "main.py": "print('hello world')\n",
        "README.md": "# Sample Project\n",
    }
    assert "data.bin" not in artifact.content
