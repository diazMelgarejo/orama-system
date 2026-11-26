"""install.sh --with-agent-scripts clones a third-party repo, so it must stay on one reviewed commit."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install.sh"
PINNED = "deb19f5896fa652c2731186f5d03bcd0193c123c"


def _text() -> str:
    return INSTALL.read_text(encoding="utf-8")


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def _upstream(tmp: Path) -> tuple[Path, str, str]:
    repo = tmp / "upstream"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "a.txt").write_text("one", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "first")
    first = _git(repo, "rev-parse", "HEAD")
    (repo / "a.txt").write_text("two", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "second")
    return repo, first, _git(repo, "rev-parse", "HEAD")


def _bootstrap(tmp: Path, repo: Path, ref: str) -> subprocess.CompletedProcess[str]:
    """Run only the bootstrap block of install.sh against a local fake upstream."""
    text = _text()
    variables = "\n".join(
        line
        for line in text.splitlines()
        if re.match(r"^(STEIPETE_REPO|STEIPETE_REF|AGENT_SCRIPTS_CLONE|AGENT_SCRIPTS_LINK)=", line)
    )
    start = text.index("agent_scripts_origin_ok() {")
    end = text.index('if [[ "${WITH_AGENT_SCRIPTS:-0}" == "1" ]]')
    harness = (
        "info(){ :; }; ok(){ :; }; warn(){ echo \"WARN: $*\" >&2; }\n"
        + variables
        + "\n"
        + text[start:end]
        + "\nbootstrap_agent_scripts\n"
    )
    home = tmp / "home"
    home.mkdir(exist_ok=True)
    return subprocess.run(
        ["bash", "-c", harness],
        capture_output=True,
        text=True,
        env={
            "HOME": str(home),
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "STEIPETE_REPO": str(repo),
            "AGENT_SCRIPTS_REF": ref,
        },
    )


def test_the_pin_is_a_full_commit_id_with_a_deliberate_override() -> None:
    text = _text()
    assert re.search(r'^STEIPETE_REF="\$\{AGENT_SCRIPTS_REF:-[0-9a-f]{40}\}"', text, re.M), "40-hex pin"
    assert f"AGENT_SCRIPTS_REF:-{PINNED}" in text, "pin must be the reviewed upstream commit"


def test_the_bootstrap_never_follows_the_upstream_tip() -> None:
    block = _text().split("agent_scripts_origin_ok() {", 1)[1].split('if [[ "${WITH_AGENT_SCRIPTS', 1)[0]
    assert "pull --ff-only" not in block.replace("run: git", ""), "a pull would move off the pin"
    assert "clone --no-checkout" in block, "a failed pin checkout must not leave unpinned files"


def test_a_clone_lands_on_the_pinned_commit_not_the_tip(tmp_path: Path) -> None:
    repo, first, second = _upstream(tmp_path)
    done = _bootstrap(tmp_path, repo, first)
    assert done.returncode == 0, done.stderr
    clone = tmp_path / "home/.agent-scripts"
    assert _git(clone, "rev-parse", "HEAD") == first != second
    assert (clone / "a.txt").read_text(encoding="utf-8") == "one"


def test_a_refresh_keeps_the_pin_when_upstream_moves_on(tmp_path: Path) -> None:
    repo, first, _second = _upstream(tmp_path)
    assert _bootstrap(tmp_path, repo, first).returncode == 0
    (repo / "a.txt").write_text("three", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "third")
    done = _bootstrap(tmp_path, repo, first)
    assert done.returncode == 0, done.stderr
    assert _git(tmp_path / "home/.agent-scripts", "rev-parse", "HEAD") == first


def test_an_unknown_pin_warns_and_leaves_no_checked_out_files(tmp_path: Path) -> None:
    repo, _first, _second = _upstream(tmp_path)
    done = _bootstrap(tmp_path, repo, "0" * 40)
    assert "WARN" in done.stderr
    assert not (tmp_path / "home/.agent-scripts/a.txt").exists(), "unpinned content must not be left behind"
    assert not (tmp_path / "home/Projects/agent-scripts").exists(), "symlink must not be created on pin failure"


def test_clone_materializes_files_when_pinned_commit_is_default_branch_tip(tmp_path: Path) -> None:
    repo, _first, second = _upstream(tmp_path)
    # Requested pin equals the default branch tip; clone --no-checkout must materialize files
    done = _bootstrap(tmp_path, repo, second)
    assert done.returncode == 0, done.stderr
    clone = tmp_path / "home/.agent-scripts"
    assert _git(clone, "rev-parse", "HEAD") == second
    assert (clone / "a.txt").exists(), "files must be checked out even when pin matches HEAD"
    assert (clone / "a.txt").read_text(encoding="utf-8") == "two"
    assert (tmp_path / "home/Projects/agent-scripts").is_symlink()


def test_pin_failure_skips_symlink(tmp_path: Path) -> None:
    repo, _first, _second = _upstream(tmp_path)
    done = _bootstrap(tmp_path, repo, "deadbeef" * 5)
    assert "WARN" in done.stderr
    assert not (tmp_path / "home/Projects/agent-scripts").exists()
