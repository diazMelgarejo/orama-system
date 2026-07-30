"""Tests for scripts/git/check_no_pending_merge.sh."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/git/check_no_pending_merge.sh"

pytestmark = pytest.mark.unit


def test_check_no_pending_merge_passes_without_in_progress_ops(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], check=True, cwd=repo)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        check=True,
        cwd=repo,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        check=True,
        cwd=repo,
    )
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], check=True, cwd=repo)
    subprocess.run(["git", "commit", "-m", "init"], check=True, cwd=repo)

    subprocess.run(["bash", str(SCRIPT), str(repo)], check=True, cwd=ROOT)


def test_check_no_pending_merge_blocks_uncommitted_merge_head(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], check=True, cwd=repo)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        check=True,
        cwd=repo,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        check=True,
        cwd=repo,
    )
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], check=True, cwd=repo)
    subprocess.run(["git", "commit", "-m", "base"], check=True, cwd=repo)
    subprocess.run(["git", "branch", "side"], check=True, cwd=repo)
    (repo / "README.md").write_text("main-line\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], check=True, cwd=repo)
    subprocess.run(["git", "commit", "-m", "main"], check=True, cwd=repo)
    subprocess.run(["git", "checkout", "side"], check=True, cwd=repo)
    (repo / "README.md").write_text("side\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], check=True, cwd=repo)
    subprocess.run(["git", "commit", "-m", "side"], check=True, cwd=repo)
    subprocess.run(["git", "checkout", "main"], check=True, cwd=repo)
    merge = subprocess.run(
        ["git", "merge", "--no-commit", "side"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert merge.returncode != 0, "expected a conflicted merge to leave MERGE_HEAD set"

    result = subprocess.run(
        ["bash", str(SCRIPT), str(repo)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "MERGE_HEAD" in result.stderr
    assert "pre-push: blocked" in result.stderr


def test_check_no_pending_merge_shell_syntax() -> None:
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True, cwd=ROOT)
