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
    repo: Path,
    patterns: Path,
    isolated_home: Path,
    diag_token: str = "",
    diag_rel: str = "scripts/cursor/seed-banned-attribution-patterns.sh",
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
    if result.returncode == 0 and diag_token:
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

        # The trace shows `rg -F -i -n -- "$token" "$rel"` running and
        # returning no match even though "$rel" demonstrably contains
        # "$token" -- with the scanner's own `2>/dev/null` hiding whatever
        # rg has to say about it. ripgrep silently skips files matched by
        # ignore rules even when the file is passed explicitly on the
        # command line (a well-documented ripgrep behavior, not a bug) --
        # run the same search directly, uncensored, with --debug and
        # --no-ignore variants to tell "genuinely no match" apart from
        # "ripgrep decided to skip this file".
        rg_direct = subprocess.run(
            ["rg", "-F", "-i", "-n", "--", diag_token, diag_rel],
            cwd=repo, capture_output=True, text=True, env=env,
        )
        rg_debug = subprocess.run(
            ["rg", "--debug", "-F", "-i", "-n", "--", diag_token, diag_rel],
            cwd=repo, capture_output=True, text=True, env=env,
        )
        rg_noignore = subprocess.run(
            ["rg", "--no-ignore", "-F", "-i", "-n", "--", diag_token, diag_rel],
            cwd=repo, capture_output=True, text=True, env=env,
        )
        rg_version = subprocess.run(["rg", "--version"], capture_output=True, text=True, env=env)
        file_bytes = (repo / diag_rel).read_bytes()
        result.rg_diag = (  # type: ignore[attr-defined]
            f"rg_version={rg_version.stdout!r}\n"
            f"rg_direct: rc={rg_direct.returncode} stdout={rg_direct.stdout!r} stderr={rg_direct.stderr!r}\n"
            f"rg_debug: rc={rg_debug.returncode} stdout={rg_debug.stdout!r} stderr={rg_debug.stderr!r}\n"
            f"rg_noignore: rc={rg_noignore.returncode} stdout={rg_noignore.stdout!r} stderr={rg_noignore.stderr!r}\n"
            f"file_bytes={file_bytes!r}"
        )
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

    result = _run_scan(repo, patterns, home, diag_token="forbidden_attribution")

    assert result.returncode == 1, (
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}\n"
        f"trace={getattr(result, 'trace', '<not captured>')}\n"
        f"rg_diag={getattr(result, 'rg_diag', '<not captured>')}"
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

    result = _run_scan(repo, patterns, home, diag_token="real-banned-value")

    assert result.returncode == 1, (
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}\n"
        f"trace={getattr(result, 'trace', '<not captured>')}\n"
        f"rg_diag={getattr(result, 'rg_diag', '<not captured>')}"
    )
    assert "scripts/cursor/seed-banned-attribution-patterns.sh" in result.stderr
