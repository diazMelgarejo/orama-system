"""Tests for scripts/git/find_stranded_work.sh."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/git/find_stranded_work.sh"


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _commit(repo: Path, filename: str, body: str, message: str) -> None:
    path = repo / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    _git(repo, "add", filename)
    _git(repo, "commit", "-m", message)


def _make_pushed_repo(tmp_path: Path) -> Path:
    mother = tmp_path / "workspace"
    repo = mother / "orama-system"
    remote = tmp_path / "remote.git"
    repo.mkdir(parents=True)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _commit(repo, "README.md", "base\n", "base")
    _git(tmp_path, "init", "--bare", str(remote))
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "main")
    return repo


def _run_scanner(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )


def test_branch_with_no_upstream_is_flagged(tmp_path: Path) -> None:
    repo = _make_pushed_repo(tmp_path)
    _git(repo, "checkout", "-b", "local-only")
    _commit(repo, "local.txt", "local\n", "local only work")
    _git(repo, "checkout", "main")

    result = _run_scanner(repo)

    assert result.returncode == 0, result.stderr
    assert "repo: " in result.stdout
    assert "branch: local-only" in result.stdout
    assert "issue: no-upstream" in result.stdout


def test_branch_not_yet_in_main_is_flagged_needs_reanchor(tmp_path: Path) -> None:
    """Merged/orphaned classification uses reanchor_scan.sh's tree-twin scan,
    not ahead/behind counts -- a branch with commits that never landed in
    main is NEEDS-REANCHOR regardless of whether it was ever pushed."""
    repo = _make_pushed_repo(tmp_path)
    _git(repo, "checkout", "-b", "ahead")
    _commit(repo, "ahead-base.txt", "base\n", "ahead branch base")
    _git(repo, "push", "-u", "origin", "ahead")
    _commit(repo, "ahead-local.txt", "local\n", "unpushed local work")
    _git(repo, "checkout", "main")

    result = _run_scanner(repo)

    assert result.returncode == 0, result.stderr
    assert "branch: ahead" in result.stdout
    assert "issue: needs-reanchor" in result.stdout
    assert "NEEDS-REANCHOR: graft 2 unique commit(s)" in result.stdout


def test_branch_already_merged_into_main_is_not_flagged(tmp_path: Path) -> None:
    """A branch whose tip is a tree-twin already in main's history (i.e.
    genuinely merged, not just pushed) is not stranded work."""
    repo = _make_pushed_repo(tmp_path)
    _git(repo, "checkout", "-b", "clean")
    _commit(repo, "clean.txt", "clean\n", "clean branch work")
    _git(repo, "push", "-u", "origin", "clean")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--no-ff", "-m", "merge clean into main", "clean")
    _git(repo, "push", "origin", "main")

    result = _run_scanner(repo)

    assert result.returncode == 0, result.stderr
    assert "branch: clean" not in result.stdout


def test_dirty_worktree_is_flagged(tmp_path: Path) -> None:
    repo = _make_pushed_repo(tmp_path)
    _git(repo, "checkout", "-b", "dirty-branch")
    _commit(repo, "dirty-base.txt", "base\n", "dirty branch base")
    _git(repo, "push", "-u", "origin", "dirty-branch")
    _git(repo, "checkout", "main")
    worktree = tmp_path / "workspace" / "dirty-worktree"
    _git(repo, "worktree", "add", str(worktree), "dirty-branch")
    (worktree / "untracked.txt").write_text("dirty\n", encoding="utf-8")

    result = _run_scanner(repo)

    assert result.returncode == 0, result.stderr
    assert f"worktree: {worktree}" in result.stdout
    assert "branch: dirty-branch" in result.stdout
    assert "issue: dirty-worktree" in result.stdout
    assert "?? untracked.txt" in result.stdout
