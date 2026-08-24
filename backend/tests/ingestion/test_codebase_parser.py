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


def test_parse_codebase_zip_handles_empty_zip():
    zip_bytes = _build_zip_bytes({})

    artifact = parse_codebase_zip(zip_bytes)

    assert artifact.artifact_type == "codebase"
    assert artifact.name == "codebase"
    assert artifact.content == {}


def test_parse_codebase_zip_all_binary_files_yields_empty_content():
    zip_bytes = _build_zip_bytes(
        {
            "data1.bin": b"\xff\xfe\x00\x01binary-garbage\x80\x81",
            "data2.bin": b"\x00\x01\x02\x03\xf8\xf9",
        }
    )

    artifact = parse_codebase_zip(zip_bytes)

    assert artifact.content == {}
    assert artifact.name == "codebase"


def test_parse_codebase_zip_derives_name_from_top_level_directory():
    zip_bytes = _build_zip_bytes(
        {
            "sample_repo/main.py": b"print('hi')\n",
            "sample_repo/lib/util.py": b"def util():\n    return 1\n",
        }
    )

    artifact = parse_codebase_zip(zip_bytes)

    assert artifact.name == "sample_repo"
    assert artifact.content == {
        "sample_repo/main.py": "print('hi')\n",
        "sample_repo/lib/util.py": "def util():\n    return 1\n",
    }
