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


def _run_scan(
    repo: Path, patterns: Path, isolated_home: Path, path_dirs: list[str] | None = None
) -> subprocess.CompletedProcess[str]:
    # Build a minimal, explicit environment rather than os.environ.copy() +
    # one override. banned_patterns_file() falls back through
    # $OPENCLAW_ATTRIBUTION_PATTERNS to $HOME/.cursor/openclaw/... to
    # $REPO_ROOT/.cursor/private/... -- inheriting the real ambient
    # environment (a developer's or CI runner's actual $HOME, PATH additions
    # from other tools, etc.) means this test's result can depend on
    # whatever happens to exist on the machine running it, not just on the
    # fixture it explicitly sets up. Pin PATH and HOME to known values and
    # set only the one variable the test cares about.
    path = os.pathsep.join(path_dirs) if path_dirs is not None else os.environ.get("PATH", "/usr/bin:/bin")
    env = {
        "PATH": path,
        "HOME": str(isolated_home),
        "OPENCLAW_ATTRIBUTION_PATTERNS": str(patterns),
    }
    return subprocess.run(
        ["bash", "scripts/git/scan-tracked-banned-tokens.sh"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


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
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
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
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "scripts/cursor/seed-banned-attribution-patterns.sh" in result.stderr


def test_fails_loudly_when_ripgrep_is_missing(tmp_path: Path) -> None:
    # Regression test for the actual bug this file's diagnostic instrumentation
    # uncovered: `rg ... 2>/dev/null || true` inside the scan loop means a
    # missing `rg` binary produces zero hits, not an error -- the scanner then
    # reports "OK: no banned tokens" even though it never actually scanned
    # anything. This silently passed on GitHub Actions runners lacking
    # ripgrep, on both this test suite and the production git-hygiene CI gate.
    # A missing dependency must fail loudly, never masquerade as "clean".
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

    # A PATH with the directory containing `rg` removed, but still real enough
    # to find bash/git/coreutils.
    rg_path = shutil.which("rg")
    if rg_path is None:
        pytest.skip("ripgrep is not installed on this machine; nothing to strip from PATH")
    rg_dir = str(Path(rg_path).parent)
    all_dirs = [d for d in os.environ.get("PATH", "/usr/bin:/bin").split(os.pathsep) if d]
    stripped_path = [d for d in all_dirs if d != rg_dir]
    if shutil.which("rg", path=os.pathsep.join(stripped_path)):
        pytest.skip("rg is also reachable from another PATH entry on this machine")

    result = _run_scan(repo, patterns, home, path_dirs=stripped_path)

    assert result.returncode != 0, (
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "ripgrep" in result.stderr.lower()
    assert "OK: no banned tokens" not in result.stdout
