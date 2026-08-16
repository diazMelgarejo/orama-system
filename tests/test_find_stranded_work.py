"""Tests for scripts/git/find_stranded_work.sh."""

from __future__ import annotations

import shutil
import stat
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/git/find_stranded_work.sh"
SCRIPT_GIT_DIR = REPO_ROOT / "scripts/git"


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


def _run_scanner_with_broken_reanchor(repo: Path, tmp_path: Path, *, missing: bool) -> subprocess.CompletedProcess[str]:
    """Run a copy of scripts/git/ with reanchor_scan.sh either removed
    (missing) or replaced with a non-executable stub, so the fail-closed
    path in print_branch_issues() can be exercised without mutating the
    real repo's guard scripts."""
    scripts_copy = tmp_path / "scripts-copy"
    shutil.copytree(SCRIPT_GIT_DIR, scripts_copy)
    reanchor_copy = scripts_copy / "reanchor_scan.sh"
    if missing:
        reanchor_copy.unlink()
    else:
        reanchor_copy.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        reanchor_copy.chmod(reanchor_copy.stat().st_mode & ~stat.S_IEXEC & ~stat.S_IXGRP & ~stat.S_IXOTH)
    return subprocess.run(
        ["bash", str(scripts_copy / "find_stranded_work.sh")],
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


def test_missing_reanchor_scanner_fails_closed(tmp_path: Path) -> None:
    """A missing/unreadable reanchor_scan.sh must be a visible, nonzero-exit
    error -- never silently reported as 'nothing to report'."""
    repo = _make_pushed_repo(tmp_path)
    _git(repo, "checkout", "-b", "ahead")
    _commit(repo, "ahead.txt", "ahead\n", "ahead work")
    _git(repo, "checkout", "main")

    result = _run_scanner_with_broken_reanchor(repo, tmp_path, missing=True)

    assert result.returncode != 0
    assert "ERROR" in result.stderr
    assert "reanchor_scan.sh missing or not executable" in result.stderr
    assert "No stranded work found." not in result.stdout


def test_non_executable_reanchor_scanner_fails_closed(tmp_path: Path) -> None:
    repo = _make_pushed_repo(tmp_path)

    result = _run_scanner_with_broken_reanchor(repo, tmp_path, missing=False)

    assert result.returncode != 0
    assert "ERROR" in result.stderr
    assert "reanchor_scan.sh missing or not executable" in result.stderr
    assert "No stranded work found." not in result.stdout


def test_unresolved_origin_main_fails_closed(tmp_path: Path) -> None:
    """reanchor_scan.sh itself exits 0 even when origin/main can't be
    resolved (it prints "no origin/main" and continues) -- the caller must
    treat that as an error, not proof the scan ran cleanly."""
    mother = tmp_path / "workspace"
    repo = mother / "orama-system"
    remote = tmp_path / "remote.git"
    repo.mkdir(parents=True)
    _git(repo, "init", "-b", "trunk")  # deliberately not "main"
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _commit(repo, "README.md", "base\n", "base")
    _git(tmp_path, "init", "--bare", str(remote))
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "trunk")  # origin/main never created

    result = _run_scanner(repo)

    assert result.returncode != 0
    assert "ERROR" in result.stderr
    assert "could not resolve origin/main" in result.stderr
    assert "No stranded work found." not in result.stdout


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
