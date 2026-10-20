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


def test_staged_rename_is_still_treated_as_a_deletion(tmp_path: Path) -> None:
    """Configured rename detection must not hide a whole-file removal."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    subprocess.run(["git", "config", "diff.renames", "true"], check=True, cwd=repo)
    (repo / "tracked.txt").unlink()
    (repo / "renamed.txt").write_text("tracked with one revision\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], check=True, cwd=repo)

    result = _run(repo, "--staged")

    assert result.returncode == EXIT_FILE_DELETION
    assert "tracked.txt" in result.stderr


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
    assert f"--source={base}" in result.stderr


def test_outgoing_range_restore_hint_uses_range_start(tmp_path: Path) -> None:
    """A multi-commit range cannot safely restore every deletion from HEAD^."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    (repo / "intermediate.txt").write_text("intermediate\n", encoding="utf-8")
    subprocess.run(["git", "add", "intermediate.txt"], check=True, cwd=repo)
    subprocess.run(["git", "commit", "-m", "intermediate"], check=True, cwd=repo)
    _stage_deletion(repo)
    subprocess.run(["git", "commit", "-m", "delete tracked file"], check=True, cwd=repo)

    result = _run(repo, "--range", f"{base}..HEAD")

    assert result.returncode == EXIT_FILE_DELETION
    assert f"--source={base}" in result.stderr
    assert "--source=HEAD^" not in result.stderr


def test_guard_is_wired_at_commit_and_push_boundaries() -> None:
    pre_commit = (ROOT / ".githooks/pre-commit").read_text(encoding="utf-8")
    pre_push = (ROOT / ".githooks/pre-push").read_text(encoding="utf-8")

    assert "check_file_deletion_guard.sh\" --staged" in pre_commit
    assert "check_file_deletion_guard.sh\" --range" in pre_push


def test_script_is_bash_32_syntax_compatible() -> None:
    result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


# ---- exact renames are moves, not deletions -------------------------------------------------
# Rename detection stays OFF for similar files (the #349 case above: a revised copy must not hide
# a removal) but an EXACT rename (100% similarity) carries every byte to the new path, so it is a
# move. The guard asks git for exact renames explicitly, independent of any diff.renames config.


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, cwd=repo, capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()


@pytest.mark.parametrize("renames_config", [None, "true", "false"])
def test_staged_exact_git_mv_is_not_a_deletion(tmp_path: Path, renames_config: str | None) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    if renames_config is not None:
        _git(repo, "config", "diff.renames", renames_config)
    _git(repo, "mv", "tracked.txt", "moved.txt")

    result = _run(repo, "--staged")

    assert result.returncode == EXIT_OK
    assert result.stderr == ""


def test_staged_exact_move_into_a_subdirectory_is_not_a_deletion(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "nested").mkdir()
    _git(repo, "mv", "tracked.txt", "nested/tracked.txt")

    assert _run(repo, "--staged").returncode == EXIT_OK


def test_outgoing_range_exact_rename_is_not_a_deletion(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "mv", "tracked.txt", "moved.txt")
    _git(repo, "commit", "-q", "-m", "move")

    result = _run(repo, "--range", f"{base}..HEAD")

    assert result.returncode == EXIT_OK
    assert result.stderr == ""


def test_exact_rename_beside_a_real_deletion_blocks_only_the_deletion(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "other.txt").write_text("other content that is different\n", encoding="utf-8")
    _git(repo, "add", "other.txt")
    _git(repo, "commit", "-q", "-m", "other")
    _git(repo, "mv", "tracked.txt", "moved.txt")
    _git(repo, "rm", "-q", "other.txt")

    result = _run(repo, "--staged")

    assert result.returncode == EXIT_FILE_DELETION
    assert "D  other.txt" in result.stderr
    assert "tracked.txt" not in result.stderr
    assert "moved.txt" not in result.stderr


def test_a_rename_with_a_single_edit_is_still_a_deletion_in_a_range(tmp_path: Path) -> None:
    """The pre-push range check keeps the #349 protection: a revised copy hides nothing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _git(repo, "config", "diff.renames", "true")
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "mv", "tracked.txt", "moved.txt")
    (repo / "moved.txt").write_text("tracked\none appended line\n", encoding="utf-8")
    _git(repo, "add", "moved.txt")
    _git(repo, "commit", "-q", "-m", "move and edit")

    result = _run(repo, "--range", f"{base}..HEAD")

    assert result.returncode == EXIT_FILE_DELETION
    assert "tracked.txt" in result.stderr


def test_a_plain_deletion_is_still_blocked_after_an_unrelated_exact_rename(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "keep.txt").write_text("keep\n", encoding="utf-8")
    _git(repo, "add", "keep.txt")
    _git(repo, "commit", "-q", "-m", "keep")
    _git(repo, "mv", "keep.txt", "kept.txt")
    _git(repo, "rm", "-q", "tracked.txt")

    result = _run(repo, "--staged")

    assert result.returncode == EXIT_FILE_DELETION
    assert "D  tracked.txt" in result.stderr


def test_a_one_line_edit_of_a_larger_file_is_not_an_exact_rename(tmp_path: Path) -> None:
    """At git's default 50% threshold this move-and-edit would read as a rename and mask the change."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    body = "".join(f"line {number}\n" for number in range(40))
    (repo / "big.txt").write_text(body, encoding="utf-8")
    _git(repo, "add", "big.txt")
    _git(repo, "commit", "-q", "-m", "big")
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "mv", "big.txt", "bigger.txt")
    (repo / "bigger.txt").write_text(body.replace("line 20\n", "line twenty\n"), encoding="utf-8")
    _git(repo, "add", "bigger.txt")
    _git(repo, "commit", "-q", "-m", "move and edit one line")
    assert "R" in _git(repo, "diff", "--name-status", "-M", f"{base}..HEAD")  # default detection hides it

    result = _run(repo, "--range", f"{base}..HEAD")

    assert result.returncode == EXIT_FILE_DELETION
    assert "big.txt" in result.stderr
