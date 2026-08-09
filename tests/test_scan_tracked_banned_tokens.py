"""Tests for scripts/git/scan-tracked-banned-tokens.sh."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/git/scan-tracked-banned-tokens.sh"
LIB = ROOT / "scripts/git/banned_attribution_lib.sh"

pytestmark = pytest.mark.unit


def _init_fixture_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
    scripts_git = repo / "scripts/git"
    scripts_git.mkdir(parents=True)
    shutil.copy2(SCRIPT, scripts_git / SCRIPT.name)
    shutil.copy2(LIB, scripts_git / LIB.name)
    patterns = tmp_path / "patterns"
    return repo, patterns


def _run_scan(repo: Path, patterns: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["OPENCLAW_ATTRIBUTION_PATTERNS"] = str(patterns)
    return subprocess.run(
        ["bash", "scripts/git/scan-tracked-banned-tokens.sh"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def test_key_name_collision_is_line_scoped_for_internal_bootstrap_files(tmp_path: Path) -> None:
    repo, patterns = _init_fixture_repo(tmp_path)
    patterns.write_text("forbidden_attribution\n", encoding="utf-8")
    target = repo / "scripts/cursor/seed-banned-attribution-patterns.sh"
    target.parent.mkdir(parents=True)
    target.write_text(
        'list_private_literal_values "$ORAMA_ROOT" forbidden_attribution\n',
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "add", "scripts/cursor/seed-banned-attribution-patterns.sh"],
        cwd=repo,
        check=True,
    )

    result = _run_scan(repo, patterns)

    assert result.returncode == 0, result.stderr


def test_internal_bootstrap_files_still_fail_on_other_banned_values(tmp_path: Path) -> None:
    repo, patterns = _init_fixture_repo(tmp_path)
    patterns.write_text("real-banned-value\n", encoding="utf-8")
    target = repo / "scripts/cursor/seed-banned-attribution-patterns.sh"
    target.parent.mkdir(parents=True)
    target.write_text("echo real-banned-value\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "scripts/cursor/seed-banned-attribution-patterns.sh"],
        cwd=repo,
        check=True,
    )

    result = _run_scan(repo, patterns)

    assert result.returncode == 1
    assert "scripts/cursor/seed-banned-attribution-patterns.sh" in result.stderr
