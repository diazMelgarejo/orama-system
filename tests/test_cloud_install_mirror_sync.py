"""A sibling mirror is only synced when doing so cannot destroy anyone's work.

``clone_sibling`` used to reset an existing checkout to ``origin/<branch>`` without
looking. The qualified-use gate for that reset needs a clean tree and no unique
unpushed commits, checked, not assumed, and the target must be an exact SHA. These
tests pin the three outcomes: synced, refused because dirty, refused because the
checkout holds commits the remote does not.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

CURSOR = Path(__file__).resolve().parents[1] / "scripts" / "cursor"
LIB = CURSOR / "lib-mirror-sync.sh"
INSTALL = CURSOR / "cloud-install.sh"
BRANCH = "main"
SYNCED, DIRTY, UNIQUE = 0, 10, 11

_GIT = ["git", "-c", "user.name=mirror-test", "-c", "user.email=mirror-test@example.invalid",
        "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]


def _git(cwd: Path, *args: str) -> str:
    """Run git in ``cwd`` and return stripped stdout, failing the test on error."""
    done = subprocess.run([*_GIT, *args], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _commit(repo: Path, name: str, text: str = "x\n") -> str:
    """Write one file, commit it, and return the new commit SHA."""
    (repo / name).write_text(text, encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", f"add {name}")
    return _git(repo, "rev-parse", "HEAD")


def _sync(mirror: Path, branch: str = BRANCH) -> subprocess.CompletedProcess[str]:
    """Call the library function the way ``cloud-install.sh`` does."""
    return subprocess.run(
        ["bash", "-c", 'source "$1"; mirror_sync_checkout "$2" "$3"', "_", str(LIB), str(mirror), branch],
        capture_output=True, text=True, check=False,
    )


@pytest.fixture
def pair(tmp_path: Path) -> tuple[Path, Path]:
    """An upstream work repo and a mirror cloned from it (both on ``main``)."""
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _git(upstream, "init", "-q")
    _commit(upstream, "base.txt")
    mirror = tmp_path / "mirror"
    _git(tmp_path, "clone", "-q", str(upstream), str(mirror))
    return upstream, mirror


def test_a_clean_mirror_behind_origin_is_moved_to_the_exact_remote_sha(pair: tuple[Path, Path]) -> None:
    """The ordinary case: nothing local, remote moved on, mirror follows it."""
    upstream, mirror = pair
    tip = _commit(upstream, "next.txt")

    result = _sync(mirror)

    assert result.returncode == SYNCED, result.stderr
    assert _git(mirror, "rev-parse", "HEAD") == tip
    assert (mirror / "next.txt").exists()


def test_an_up_to_date_mirror_is_a_no_op(pair: tuple[Path, Path]) -> None:
    """Re-running on a current mirror succeeds and changes nothing."""
    _, mirror = pair
    before = _git(mirror, "rev-parse", "HEAD")

    assert _sync(mirror).returncode == SYNCED
    assert _git(mirror, "rev-parse", "HEAD") == before


def test_a_modified_tracked_file_is_refused_and_left_intact(pair: tuple[Path, Path]) -> None:
    """Someone edited the mirror: refuse, never erase."""
    upstream, mirror = pair
    _commit(upstream, "next.txt")
    (mirror / "base.txt").write_text("local edit\n", encoding="utf-8")

    result = _sync(mirror)

    assert result.returncode == DIRTY
    assert (mirror / "base.txt").read_text(encoding="utf-8") == "local edit\n"
    assert not (mirror / "next.txt").exists()  # nothing was moved


def test_an_untracked_file_is_refused_and_left_intact(pair: tuple[Path, Path]) -> None:
    """Untracked work is exactly what a reset-based sync silently keeps or clobbers."""
    upstream, mirror = pair
    _commit(upstream, "next.txt")
    (mirror / "scratch.txt").write_text("keep me\n", encoding="utf-8")

    result = _sync(mirror)

    assert result.returncode == DIRTY
    assert (mirror / "scratch.txt").read_text(encoding="utf-8") == "keep me\n"


def test_a_unique_local_commit_is_refused_and_stays_reachable(pair: tuple[Path, Path]) -> None:
    """A commit the remote lacks is unpushed work; the branch must not move."""
    upstream, mirror = pair
    _commit(upstream, "next.txt")
    mine = _commit(mirror, "mine.txt")

    result = _sync(mirror)

    assert result.returncode == UNIQUE
    assert _git(mirror, "rev-parse", "HEAD") == mine
    assert (mirror / "mine.txt").exists()


def test_a_unique_commit_on_a_different_branch_head_is_refused(pair: tuple[Path, Path]) -> None:
    """The checkout may sit on another branch; its unpushed commit is still at risk."""
    upstream, mirror = pair
    _commit(upstream, "next.txt")
    _git(mirror, "checkout", "-q", "-b", "feature")
    mine = _commit(mirror, "mine.txt")

    result = _sync(mirror)

    assert result.returncode == UNIQUE
    assert _git(mirror, "rev-parse", "HEAD") == mine
    assert _git(mirror, "branch", "--show-current") == "feature"


def test_a_local_commit_already_landed_upstream_is_not_unique(pair: tuple[Path, Path]) -> None:
    """Patch-equivalence, not SHA equality: a rewritten-but-landed commit is safe to drop."""
    upstream, mirror = pair
    _commit(mirror, "same.txt", "same\n")
    _commit(upstream, "same.txt", "same\n")  # same change, different commit id
    tip = _commit(upstream, "after.txt")

    result = _sync(mirror)

    assert result.returncode == SYNCED, result.stderr
    assert _git(mirror, "rev-parse", "HEAD") == tip


def test_an_unreachable_origin_is_neither_synced_nor_mistaken_for_a_refusal(
    pair: tuple[Path, Path], tmp_path: Path
) -> None:
    """A fetch failure must surface as its own failure, not as success or a gate result."""
    _, mirror = pair
    _git(mirror, "remote", "set-url", "origin", str(tmp_path / "does-not-exist"))

    result = _sync(mirror)

    assert result.returncode not in (SYNCED, DIRTY, UNIQUE)


def _clone_sibling(
    home: Path, name: str, policy: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the real ``clone_sibling`` extracted from the install script, with stub logging."""
    script = (
        'source "$1"; log() { :; }; warn() { printf "WARN %s\n" "$*" >&2; }; '
        'eval "$(sed -n \'/^clone_sibling() {/,/^}/p\' "$2")"; '
        'export OPENCLAW_HOME="$3"; clone_sibling "$4" unused-url main'
    )
    env = {"PATH": __import__("os").environ["PATH"], "HOME": str(home)}
    if policy is not None:
        env["CLOUD_INSTALL_ON_DIVERGED_MIRROR"] = policy
    return subprocess.run(
        ["bash", "-c", script, "_", str(LIB), str(INSTALL), str(home), name],
        capture_output=True, text=True, check=False, env=env,
    )


@pytest.fixture
def sibling(pair: tuple[Path, Path], tmp_path: Path) -> tuple[Path, Path, Path]:
    """An OPENCLAW_HOME holding a mirror named ``Sibling`` cloned from the upstream."""
    upstream, mirror = pair
    home = tmp_path / "openclaw-home"
    home.mkdir()
    mirror.rename(home / "Sibling")
    return upstream, home, home / "Sibling"


def test_clone_sibling_syncs_a_clean_mirror(sibling: tuple[Path, Path, Path]) -> None:
    """Wiring: the ordinary boot path still brings a clean mirror current."""
    upstream, home, mirror = sibling
    tip = _commit(upstream, "next.txt")

    result = _clone_sibling(home, "Sibling")

    assert result.returncode == 0, result.stderr
    assert _git(mirror, "rev-parse", "HEAD") == tip


def test_clone_sibling_leaves_a_diverged_mirror_untouched_and_warns(
    sibling: tuple[Path, Path, Path],
) -> None:
    """Boot must not die on a diverged mirror, and must not erase it either."""
    upstream, home, mirror = sibling
    _commit(upstream, "next.txt")
    mine = _commit(mirror, "mine.txt")

    result = _clone_sibling(home, "Sibling")

    assert result.returncode == 0
    assert "NOT synced" in result.stderr and "11=unpushed commits" in result.stderr
    assert _git(mirror, "rev-parse", "HEAD") == mine


def test_clone_sibling_can_be_told_to_fail_on_a_diverged_mirror(
    sibling: tuple[Path, Path, Path],
) -> None:
    """The operator can opt into a hard failure instead of a warning."""
    upstream, home, mirror = sibling
    _commit(upstream, "next.txt")
    (mirror / "base.txt").write_text("local edit\n", encoding="utf-8")

    result = _clone_sibling(home, "Sibling", policy="fail")

    assert result.returncode == 1
    assert (mirror / "base.txt").read_text(encoding="utf-8") == "local edit\n"
