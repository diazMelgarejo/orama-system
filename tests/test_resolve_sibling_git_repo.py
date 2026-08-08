"""Tests for scripts/git/resolve_sibling_git_repo.sh's generic crawler.

resolve_perp_harness.sh's own tests (test_resolve_perp_harness.py) already
cover the PT-specific wrapper end to end; these tests exercise the generic
primitives directly, including the bash-3.2 empty-array/nounset pitfall that
motivated the defensive `${#arr[@]}` guard in sibling_repo_add_candidate.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RESOLVER_SCRIPT = REPO_ROOT / "scripts/git/resolve_sibling_git_repo.sh"


def _run(script_body: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    full = f'source "{RESOLVER_SCRIPT}"; {script_body}'
    return subprocess.run(
        ["bash", "-c", full],
        env=run_env,
        capture_output=True,
        text=True,
        check=False,
    )


def _make_repo(root: Path, marker: str = "") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir()
    if marker:
        marker_path = root / marker
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.write_text("# fixture\n", encoding="utf-8")
    return root


def test_is_git_root_requires_git_dir(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    result = _run(f'sibling_repo_is_git_root "{plain}" "" && echo YES || echo NO')
    assert result.stdout.strip() == "NO"


def test_is_git_root_empty_marker_accepts_any_git_repo(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    result = _run(f'sibling_repo_is_git_root "{repo}" "" && echo YES || echo NO')
    assert result.stdout.strip() == "YES"


def test_is_git_root_rejects_missing_marker(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    result = _run(f'sibling_repo_is_git_root "{repo}" "some/marker.py" && echo YES || echo NO')
    assert result.stdout.strip() == "NO"


def test_is_git_root_rejects_symlink(tmp_path: Path) -> None:
    real = _make_repo(tmp_path / "real")
    link = tmp_path / "link"
    link.symlink_to(real)
    result = _run(f'sibling_repo_is_git_root "{link}" "" && echo YES || echo NO')
    assert result.stdout.strip() == "NO"


def test_add_candidate_on_empty_array_does_not_crash_under_nounset(tmp_path: Path) -> None:
    """Regression test for the bash-3.2 "${arr[@]}" on an empty array pitfall."""
    repo = _make_repo(tmp_path / "repo")
    result = _run(
        f'set -u; sibling_repo_reset_candidates; '
        f'sibling_repo_add_candidate "{repo}" ""; '
        f'echo "count=${{#_sibling_repo_candidates[@]}}"'
    )
    assert result.returncode == 0, result.stderr
    assert "count=1" in result.stdout


def test_add_candidate_dedupes(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    result = _run(
        f'sibling_repo_reset_candidates; '
        f'sibling_repo_add_candidate "{repo}" ""; '
        f'sibling_repo_add_candidate "{repo}" ""; '
        f'echo "count=${{#_sibling_repo_candidates[@]}}"'
    )
    assert result.returncode == 0, result.stderr
    assert "count=1" in result.stdout


def test_crawl_collect_finds_nested_repo_at_depth(tmp_path: Path) -> None:
    """The whole point of this crawler: a repo nested deeper than 1 level
    (e.g. Perpetua-Tools under perplexity-api/) must still be found."""
    nested = _make_repo(tmp_path / "mother" / "nested" / "Target", marker="marker.txt")
    result = _run(
        f'sibling_repo_reset_candidates; '
        f'sibling_repo_crawl_collect "{tmp_path / "mother"}" "marker.txt" 2; '
        f'sibling_repo_finalize "Target"'
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(nested)


def test_crawl_collect_depth_zero_only_checks_base(tmp_path: Path) -> None:
    _make_repo(tmp_path / "mother" / "nested" / "Target", marker="marker.txt")
    result = _run(
        f'sibling_repo_reset_candidates; '
        f'sibling_repo_crawl_collect "{tmp_path / "mother"}" "marker.txt" 0; '
        f'sibling_repo_finalize "Target"'
    )
    assert result.returncode != 0


def test_finalize_fails_closed_on_ambiguous_candidates(tmp_path: Path) -> None:
    _make_repo(tmp_path / "mother" / "A", marker="marker.txt")
    _make_repo(tmp_path / "mother" / "B", marker="marker.txt")
    result = _run(
        f'sibling_repo_reset_candidates; '
        f'sibling_repo_crawl_collect "{tmp_path / "mother"}" "marker.txt" 1; '
        f'sibling_repo_finalize "Target"'
    )
    assert result.returncode != 0
    assert "ambiguous" in result.stderr.lower()


def test_check_env_override_returns_1_when_unset() -> None:
    result = _run(
        'unset FOO_PATH; sibling_repo_check_env_override "" FOO_PATH; echo "rc=$?"',
    )
    assert "rc=1" in result.stdout


def test_check_env_override_returns_2_on_invalid_explicit_override(tmp_path: Path) -> None:
    bogus = tmp_path / "not-a-repo"
    bogus.mkdir()
    result = _run(
        f'export FOO_PATH="{bogus}"; sibling_repo_check_env_override "" FOO_PATH; echo "rc=$?"',
    )
    assert "rc=2" in result.stdout


def test_check_env_override_returns_0_on_valid_override(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    result = _run(
        f'export FOO_PATH="{repo}"; sibling_repo_check_env_override "" FOO_PATH',
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(repo)
