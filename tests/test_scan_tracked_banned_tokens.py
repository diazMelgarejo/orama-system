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


def _init_fixture_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
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
    isolated_home = tmp_path / "home"
    isolated_home.mkdir()
    return repo, patterns, isolated_home


def _run_scan(repo: Path, patterns: Path, isolated_home: Path) -> subprocess.CompletedProcess[str]:
    # Build a minimal, explicit environment rather than os.environ.copy() +
    # one override. banned_patterns_file() falls back through
    # $OPENCLAW_ATTRIBUTION_PATTERNS to $HOME/.cursor/openclaw/... to
    # $REPO_ROOT/.cursor/private/... -- inheriting the real ambient
    # environment (a developer's or CI runner's actual $HOME, PATH additions
    # from other tools, etc.) means this test's result can depend on
    # whatever happens to exist on the machine running it, not just on the
    # fixture it explicitly sets up. Pin PATH and HOME to known values and
    # set only the one variable the test cares about.
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(isolated_home),
        "OPENCLAW_ATTRIBUTION_PATTERNS": str(patterns),
    }
    result = subprocess.run(
        ["bash", "scripts/git/scan-tracked-banned-tokens.sh"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode == 0:
        # Diagnostic-only: this scanner unexpectedly reported clean in some
        # environments (passes locally, in a fresh clone, and in a sandboxed
        # agent run, but has failed intermittently in CI) with no other
        # signal to explain why. Re-run with `bash -x` and stash the full
        # execution trace on the result object so a failing assertion can
        # surface exactly which branch was taken and what each resolved
        # value was, without needing another round-trip to reproduce it.
        trace = subprocess.run(
            ["bash", "-x", "scripts/git/scan-tracked-banned-tokens.sh"],
            cwd=repo,
            capture_output=True,
            text=True,
            env=env,
        )
        result.trace = trace.stderr  # type: ignore[attr-defined]
    return result


def test_key_name_collision_is_line_scoped_for_internal_bootstrap_files(tmp_path: Path) -> None:
    repo, patterns, home = _init_fixture_repo(tmp_path)
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

    result = _run_scan(repo, patterns, home)

    assert result.returncode == 0, result.stderr


def test_key_name_collision_rejects_non_key_name_occurrence(tmp_path: Path) -> None:
    repo, patterns, home = _init_fixture_repo(tmp_path)
    patterns.write_text("forbidden_attribution\n", encoding="utf-8")
    target = repo / "scripts/cursor/seed-banned-attribution-patterns.sh"
    target.parent.mkdir(parents=True)
    target.write_text("echo forbidden_attribution\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "scripts/cursor/seed-banned-attribution-patterns.sh"],
        cwd=repo,
        check=True,
    )

    result = _run_scan(repo, patterns, home)

    assert result.returncode == 1, (
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}\n"
        f"trace={getattr(result, 'trace', '<not captured>')}"
    )
    assert "scripts/cursor/seed-banned-attribution-patterns.sh" in result.stderr


def test_internal_bootstrap_files_still_fail_on_other_banned_values(tmp_path: Path) -> None:
    repo, patterns, home = _init_fixture_repo(tmp_path)
    patterns.write_text("real-banned-value\n", encoding="utf-8")
    target = repo / "scripts/cursor/seed-banned-attribution-patterns.sh"
    target.parent.mkdir(parents=True)
    target.write_text("echo real-banned-value\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "scripts/cursor/seed-banned-attribution-patterns.sh"],
        cwd=repo,
        check=True,
    )

    result = _run_scan(repo, patterns, home)

    assert result.returncode == 1, (
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}\n"
        f"trace={getattr(result, 'trace', '<not captured>')}"
    )
    assert "scripts/cursor/seed-banned-attribution-patterns.sh" in result.stderr
