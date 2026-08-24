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
