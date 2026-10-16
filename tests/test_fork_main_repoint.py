"""Re-pointing a fork's ``main`` at upstream must not destroy commits nobody declared.

Two scripts move a branch to another ref: one rewrites the fork's remote ``main`` to
upstream (after cherry-picking three declared commits elsewhere), the other moves a
local ``main`` and then its integration branch to their remotes. Both used to do it
blindly. The gate is: a clean tree, and no commit the move would leave unreferenced
other than those the caller declared. Commits another branch still holds are safe.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "scripts" / "cursor" / "lib-mirror-sync.sh"
ALPHACLAW = ROOT / "scripts" / "git" / "alphaclaw-sync-integration-with-main.sh"
DIRTY, UNIQUE = 10, 11

_GIT = ["git", "-c", "user.name=repoint-test", "-c", "user.email=repoint-test@example.invalid",
        "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]


def _git(cwd: Path, *args: str) -> str:
    """Run git in ``cwd`` and return stripped stdout, failing the test on error."""
    done = subprocess.run([*_GIT, *args], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _commit(repo: Path, name: str, text: str = "x\n") -> str:
    """Write one file, commit it, and return the commit SHA."""
    (repo / name).write_text(text, encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", f"add {name}")
    return _git(repo, "rev-parse", "HEAD")


def _repoint(work: Path, *allowed: str) -> subprocess.CompletedProcess[str]:
    """Call ``mirror_repoint_to_upstream`` as the periscope script does."""
    script = 'source "$1"; shift; mirror_repoint_to_upstream "$@"'
    return subprocess.run(
        ["bash", "-c", script, "_", str(LIB), str(work), "main", "upstream/main", "origin", *allowed],
        capture_output=True, text=True, check=False,
    )


@pytest.fixture
def fork(tmp_path: Path) -> dict[str, Path | str]:
    """upstream (bare) <- origin (bare, with two fork-only commits) <- work clone."""
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "-q")
    base = _commit(seed, "base.txt")
    upstream = tmp_path / "upstream.git"
    _git(tmp_path, "clone", "-q", "--bare", str(seed), str(upstream))
    _git(seed, "remote", "add", "up", str(upstream))
    dep_a = _commit(seed, "dep-a.txt")
    dep_b = _commit(seed, "dep-b.txt")
    origin = tmp_path / "origin.git"
    _git(tmp_path, "clone", "-q", "--bare", str(seed), str(origin))
    # Upstream moves on independently of the fork.
    _git(seed, "checkout", "-q", "-b", "up-next", base)
    up_tip = _commit(seed, "upstream-next.txt")
    _git(seed, "push", "-q", "up", f"{up_tip}:refs/heads/main")
    work = tmp_path / "work"
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    _git(work, "remote", "add", "upstream", str(upstream))
    _git(work, "fetch", "-q", "upstream")
    return {"work": work, "origin": origin, "upstream": upstream,
            "dep_a": dep_a, "dep_b": dep_b, "up_tip": up_tip, "tmp": tmp_path}


def _remote_main(bare: Path) -> str:
    """Return the tip of ``main`` in a bare repository."""
    return _git(bare, "rev-parse", "refs/heads/main")


def test_declared_commits_are_the_only_ones_dropped_and_remain_recoverable(fork) -> None:
    """The intended operation: remote main becomes upstream, declared commits are kept as a ref."""
    result = _repoint(fork["work"], fork["dep_a"], fork["dep_b"])

    assert result.returncode == 0, result.stderr
    assert _remote_main(fork["origin"]) == fork["up_tip"]
    assert _git(fork["work"], "rev-parse", "HEAD") == fork["up_tip"]
    backups = _git(fork["work"], "for-each-ref", "--format=%(refname:short)", "refs/heads/backup/").split()
    assert backups, "a recovery ref must exist before the remote is rewritten"
    assert _git(fork["work"], "merge-base", "--is-ancestor", fork["dep_b"], backups[0]) == ""


def test_an_undeclared_unique_commit_on_the_remote_blocks_the_rewrite(fork) -> None:
    """A commit nobody declared would be erased from the remote: refuse, change nothing."""
    result = _repoint(fork["work"], fork["dep_a"])  # dep_b is not declared

    assert result.returncode == UNIQUE
    assert fork["dep_b"][:7] in result.stderr
    assert _remote_main(fork["origin"]) == fork["dep_b"]


def test_a_dirty_tree_blocks_the_rewrite(fork) -> None:
    """Uncommitted work would be carried or lost by the move: refuse."""
    work = fork["work"]
    (work / "dep-a.txt").write_text("local edit\n", encoding="utf-8")

    result = _repoint(work, fork["dep_a"], fork["dep_b"])

    assert result.returncode == DIRTY
    assert (work / "dep-a.txt").read_text(encoding="utf-8") == "local edit\n"
    assert _remote_main(fork["origin"]) == fork["dep_b"]


def test_an_unpushed_local_commit_blocks_the_rewrite(fork) -> None:
    """Local main work that exists nowhere else would be lost: refuse."""
    mine = _commit(fork["work"], "mine.txt")

    result = _repoint(fork["work"], fork["dep_a"], fork["dep_b"])

    assert result.returncode == UNIQUE
    assert mine[:7] in result.stderr
    assert _git(fork["work"], "rev-parse", "HEAD") == mine


def test_repointing_an_already_current_fork_is_a_no_op(fork) -> None:
    """Idempotent: run twice and the second run changes nothing and pushes nothing."""
    assert _repoint(fork["work"], fork["dep_a"], fork["dep_b"]).returncode == 0
    before = _remote_main(fork["origin"])

    again = _repoint(fork["work"], fork["dep_a"], fork["dep_b"])

    assert again.returncode == 0, again.stderr
    assert _remote_main(fork["origin"]) == before == fork["up_tip"]


# ---- alphaclaw: local main, then the integration branch -------------------------


@pytest.fixture
def alphaclaw(tmp_path: Path) -> dict[str, Path]:
    """origin (bare) with main + integration branch, and a working checkout of it."""
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "-q")
    _commit(seed, "base.txt")
    _git(seed, "checkout", "-q", "-b", "integ")
    _commit(seed, "integ.txt")
    origin = tmp_path / "origin.git"
    _git(tmp_path, "clone", "-q", "--bare", str(seed), str(origin))
    home = tmp_path / "home"
    work = home / "AlphaClaw"
    home.mkdir()
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    _git(work, "checkout", "-q", "integ")
    return {"home": home, "work": work, "origin": origin, "seed": seed}


def _run_alphaclaw(home: Path) -> subprocess.CompletedProcess[str]:
    """Run the real sync script against the temporary AlphaClaw checkout."""
    env = {**os.environ, "OPENCLAW_HOME": str(home), "ALPHACLAW_INSTALL_DIR": str(home / "AlphaClaw"),
           "ALPHACLAW_INTEGRATION_BRANCH": "integ", "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
    return subprocess.run(["bash", str(ALPHACLAW)], capture_output=True, text=True, check=False, env=env)


def test_alphaclaw_sync_refuses_a_dirty_tree_and_keeps_the_edit(alphaclaw) -> None:
    """The old script's hard reset would have wiped this tracked modification."""
    work = alphaclaw["work"]
    (work / "integ.txt").write_text("work in progress\n", encoding="utf-8")

    result = _run_alphaclaw(alphaclaw["home"])

    assert result.returncode != 0
    assert (work / "integ.txt").read_text(encoding="utf-8") == "work in progress\n"


def test_alphaclaw_sync_refuses_unpushed_integration_commits(alphaclaw) -> None:
    """Resetting the integration branch to its remote used to drop these silently."""
    work = alphaclaw["work"]
    mine = _commit(work, "unpushed.txt")

    result = _run_alphaclaw(alphaclaw["home"])

    assert result.returncode != 0
    assert _git(work, "rev-parse", "integ") == mine


def test_alphaclaw_sync_still_works_for_a_clean_checkout(alphaclaw) -> None:
    """Wiring: a clean checkout syncs main and ends with integ containing origin/main."""
    result = _run_alphaclaw(alphaclaw["home"])

    assert result.returncode == 0, result.stderr
    work = alphaclaw["work"]
    _git(work, "merge-base", "--is-ancestor", _git(work, "rev-parse", "origin/main"), "HEAD")
