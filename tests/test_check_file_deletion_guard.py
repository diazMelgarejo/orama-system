"""Regression tests for the whole-file deletion commit and push guard."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/git/check_file_deletion_guard.sh"

pytestmark = pytest.mark.unit

EXIT_OK = 0
EXIT_FILE_DELETION = 9


def _run(repo: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command_env = os.environ.copy()
    if env:
        command_env.update(env)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=command_env,
    )


def _init_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], check=True, cwd=repo)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, cwd=repo)
    subprocess.run(["git", "config", "user.name", "Test"], check=True, cwd=repo)
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], check=True, cwd=repo)
    subprocess.run(["git", "commit", "-m", "init"], check=True, cwd=repo)


def _stage_deletion(repo: Path) -> None:
    (repo / "tracked.txt").unlink()
    subprocess.run(["git", "add", "-u"], check=True, cwd=repo)


def test_staged_clean_index_passes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    result = _run(repo, "--staged")

    assert result.returncode == EXIT_OK
    assert result.stderr == ""


def test_staged_whole_file_deletion_blocks_with_path_and_symbol(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _stage_deletion(repo)

    result = _run(repo, "--staged")

    assert result.returncode == EXIT_FILE_DELETION
    assert "GIT_SCOPE_E_FILE_DELETION" in result.stderr
    assert "tracked.txt" in result.stderr
    assert "git restore --staged" in result.stderr


@pytest.mark.parametrize(
    "env",
    [
        {"GIT_ALLOW_FILE_DELETIONS": "1"},
        {"GIT_FILE_DELETION_JUSTIFICATION": "retire obsolete fixture"},
    ],
)
def test_staged_deletion_requires_both_override_values(tmp_path: Path, env: dict[str, str]) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _stage_deletion(repo)

    result = _run(repo, "--staged", env=env)

    assert result.returncode == EXIT_FILE_DELETION


def test_staged_deletion_allows_explicit_justified_override(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _stage_deletion(repo)

    result = _run(
        repo,
        "--staged",
        env={
            "GIT_ALLOW_FILE_DELETIONS": "1",
            "GIT_FILE_DELETION_JUSTIFICATION": "retire obsolete fixture",
        },
    )

    assert result.returncode == EXIT_OK
    assert "explicitly allowed" in result.stderr


def test_outgoing_range_whole_file_deletion_blocks(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    _stage_deletion(repo)
    subprocess.run(["git", "commit", "-m", "delete tracked file"], check=True, cwd=repo)

    result = _run(repo, "--range", f"{base}..HEAD")

    assert result.returncode == EXIT_FILE_DELETION
    assert "tracked.txt" in result.stderr
    assert "git diff --name-status" in result.stderr


def test_guard_is_wired_at_commit_and_push_boundaries() -> None:
    pre_commit = (ROOT / ".githooks/pre-commit").read_text(encoding="utf-8")
    pre_push = (ROOT / ".githooks/pre-push").read_text(encoding="utf-8")

    assert "check_file_deletion_guard.sh\" --staged" in pre_commit
    assert "check_file_deletion_guard.sh\" --range" in pre_push


def test_script_is_bash_32_syntax_compatible() -> None:
    result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
