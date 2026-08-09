"""Tests for scripts/git/check_commit_message_claims.py.

The motivating regression: a commit message claimed "Added ... to
guard-sync-manifest.sh's GUARD_SYNC_EXECUTABLES" while the actual diff only
touched a header comment, never the array. This suite pins that exact case
plus the surrounding heuristic's precision/recall tradeoffs.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/git/check_commit_message_claims.py"
sys.path.insert(0, str(REPO_ROOT / "scripts/git"))

import check_commit_message_claims as ccmc  # noqa: E402


def test_regression_guard_sync_executables_claim_not_backed_by_diff(tmp_path: Path) -> None:
    msg = tmp_path / "msg.txt"
    msg.write_text(
        "feat(git): generic marker-based sibling-repo crawler, fix --workspace depth\n\n"
        "- Added to guard-sync-manifest.sh's GUARD_SYNC_EXECUTABLES so it gets\n"
        "  synced byte-identical to Perpetua-Tools/AlphaClaw.\n",
        encoding="utf-8",
    )
    body = ccmc.commit_message_body(str(msg))
    claims = ccmc.find_claims(body)
    assert "GUARD_SYNC_EXECUTABLES" in claims


def test_backtick_quoted_claim_is_detected() -> None:
    body = "Added `FOO_BAR_BAZ` to the config loader.\n"
    assert ccmc.find_claims(body) == ["FOO_BAR_BAZ"]


def test_bare_upper_snake_case_claim_is_detected_without_backticks() -> None:
    body = "Registered NEW_TOOL_NAME in the manifest array.\n"
    assert ccmc.find_claims(body) == ["NEW_TOOL_NAME"]


def test_identifier_far_from_any_verb_is_not_flagged() -> None:
    body = (
        "This paragraph discusses `SOME_CONSTANT` at length for unrelated reasons, "
        + "x" * 60
        + " and only much later does the word introduced show up, far away.\n"
    )
    assert ccmc.find_claims(body) == []


def test_reversed_order_ident_then_verb_is_detected() -> None:
    body = "`HELPER_FN` was added to the module.\n"
    assert ccmc.find_claims(body) == ["HELPER_FN"]


def test_skip_list_common_words_not_flagged() -> None:
    body = "Added THE new behavior described above.\n"
    assert ccmc.find_claims(body) == []


def test_main_exits_zero_when_no_claims(tmp_path: Path) -> None:
    msg = tmp_path / "msg.txt"
    msg.write_text("chore: routine cleanup, no code claims here\n", encoding="utf-8")
    result = subprocess.run(
        ["python3", str(SCRIPT), str(msg)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_main_exits_nonzero_when_claim_unbacked_by_staged_diff(tmp_path: Path) -> None:
    """End-to-end: a real git repo, a real (empty) staged diff, and a message
    claiming to add a symbol that appears nowhere in it."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    (repo / "f.txt").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "f.txt"], cwd=repo, check=True)

    msg = repo / "msg.txt"
    msg.write_text("Registered TOTALLY_MISSING_SYMBOL in the config.\n", encoding="utf-8")
    result = subprocess.run(
        ["python3", str(SCRIPT), str(msg)],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "TOTALLY_MISSING_SYMBOL" in result.stderr


def test_main_exits_zero_when_claim_is_backed_by_staged_diff(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    (repo / "f.txt").write_text("SOME_REAL_SYMBOL = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "f.txt"], cwd=repo, check=True)

    msg = repo / "msg.txt"
    msg.write_text("Added SOME_REAL_SYMBOL to the config.\n", encoding="utf-8")
    result = subprocess.run(
        ["python3", str(SCRIPT), str(msg)],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def _init_test_repo(repo: Path) -> None:
    repo.mkdir()
    # Pin the initial branch name explicitly -- relying on the ambient
    # init.defaultBranch config broke CI, whose runner doesn't default to
    # "main" the way this machine's global git config happens to.
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    (repo / "f.txt").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "f.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)


def test_find_git_state_claims_detects_pushed_merged_and_branch() -> None:
    body = (
        "pushed to origin/main after review\n"
        "merged into `main`\n"
        "on branch feature/foo\n"
    )
    claims = ccmc.find_git_state_claims(body)
    assert ("pushed", "origin/main") in claims
    assert ("merged", "main") in claims
    assert ("branch", "feature/foo") in claims


def test_git_state_pushed_to_origin_main_true(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_test_repo(repo)
    tip = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", tip],
        cwd=repo,
        check=True,
    )
    msg = repo / "msg.txt"
    msg.write_text("chore: pushed to origin/main\n", encoding="utf-8")
    result = subprocess.run(
        ["python3", str(SCRIPT), str(msg)],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_git_state_pushed_to_missing_ref_false(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_test_repo(repo)
    msg = repo / "msg.txt"
    msg.write_text("chore: pushed to origin/no-such-branch\n", encoding="utf-8")
    result = subprocess.run(
        ["python3", str(SCRIPT), str(msg)],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "git-state-claim check" in result.stderr
    assert "origin/no-such-branch" in result.stderr


def test_git_state_merged_into_main_is_not_precommit_validated(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_test_repo(repo)
    msg = repo / "msg.txt"
    msg.write_text("feat: merged into main\n", encoding="utf-8")
    result = subprocess.run(
        ["python3", str(SCRIPT), str(msg)],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_git_state_merged_into_main_future_claim_is_left_to_post_push_validation(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_test_repo(repo)
    subprocess.run(["git", "checkout", "-q", "-b", "feature"], cwd=repo, check=True)
    subprocess.run(["git", "checkout", "-q", "main"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "main moved ahead"], cwd=repo, check=True)
    subprocess.run(["git", "checkout", "-q", "feature"], cwd=repo, check=True)
    msg = repo / "msg.txt"
    msg.write_text("feat: merged into main\n", encoding="utf-8")
    result = subprocess.run(
        ["python3", str(SCRIPT), str(msg)],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_git_state_on_branch_true(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_test_repo(repo)
    subprocess.run(["git", "checkout", "-q", "-b", "my-feature"], cwd=repo, check=True)
    msg = repo / "msg.txt"
    msg.write_text("feat: work done on branch my-feature\n", encoding="utf-8")
    result = subprocess.run(
        ["python3", str(SCRIPT), str(msg)],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_git_state_on_branch_false(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_test_repo(repo)
    subprocess.run(["git", "checkout", "-q", "-b", "actual-branch"], cwd=repo, check=True)
    msg = repo / "msg.txt"
    msg.write_text("feat: work done on branch wrong-name\n", encoding="utf-8")
    result = subprocess.run(
        ["python3", str(SCRIPT), str(msg)],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "git-state-claim check" in result.stderr
    assert "wrong-name" in result.stderr
