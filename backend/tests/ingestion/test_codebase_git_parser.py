import os
import subprocess

from app.ingestion.codebase_parser import parse_codebase_git


def _run_git(args, cwd):
    subprocess.run(
        ["git"] + args,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _make_source_repo(tmp_path):
    source_path = tmp_path / "source_repo"
    source_path.mkdir()
    _run_git(["init"], cwd=source_path)
    _run_git(["config", "user.email", "test@example.com"], cwd=source_path)
    _run_git(["config", "user.name", "Test User"], cwd=source_path)
    (source_path / "app.py").write_text("def add(a, b):\n    return a + b\n")
    _run_git(["add", "app.py"], cwd=source_path)
    _run_git(["commit", "-m", "initial commit"], cwd=source_path)
    return source_path


def test_parse_codebase_git_clones_and_reads_tracked_files(tmp_path):
    source_path = _make_source_repo(tmp_path)
    dest_path = tmp_path / "cloned_repo"

    artifact = parse_codebase_git(str(source_path), str(dest_path))

    assert artifact.artifact_type == "codebase"
    assert artifact.name == "cloned_repo"
    assert artifact.content == {"app.py": "def add(a, b):\n    return a + b\n"}
    assert (dest_path / ".git").is_dir()


def test_parse_codebase_git_reads_nested_directories(tmp_path):
    source_path = _make_source_repo(tmp_path)
    nested_dir = source_path / "src" / "lib"
    nested_dir.mkdir(parents=True)
    (nested_dir / "util.py").write_text("def util():\n    return 1\n")
    _run_git(["add", "src/lib/util.py"], cwd=source_path)
    _run_git(["commit", "-m", "add nested file"], cwd=source_path)
    dest_path = tmp_path / "cloned_repo"

    artifact = parse_codebase_git(str(source_path), str(dest_path))

    assert artifact.content["src/lib/util.py"] == "def util():\n    return 1\n"
    assert artifact.content["app.py"] == "def add(a, b):\n    return a + b\n"


def test_parse_codebase_git_does_not_follow_symlinks_outside_checkout(tmp_path):
    secret_path = tmp_path / "secret.txt"
    secret_path.write_text("super-secret-content-outside-the-repo\n")

    source_path = _make_source_repo(tmp_path)
    symlink_path = source_path / "evil_link"
    os.symlink(secret_path, symlink_path)
    _run_git(["add", "-A"], cwd=source_path)
    _run_git(["commit", "-m", "add malicious symlink"], cwd=source_path)
    dest_path = tmp_path / "cloned_repo"

    artifact = parse_codebase_git(str(source_path), str(dest_path))

    # The cloned working tree does contain the symlink, but the parser must
    # not follow it: either the entry is absent, or if present its content
    # must not be the linked-to secret file's real content.
    assert artifact.content.get("evil_link") != "super-secret-content-outside-the-repo\n"
    assert "evil_link" not in artifact.content
