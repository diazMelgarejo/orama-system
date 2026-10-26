"""Guard sync manifest — single source of truth for attribution guard distribution."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GIT = ROOT / "scripts" / "git"
MANIFEST = GIT / "guard-sync-manifest.sh"
SYNC = GIT / "sync-attribution-guard-scripts.sh"
VERIFY = GIT / "verify-guard-parity.sh"


def _extract_sync_binding_pattern() -> str:
    """Pull the actual grep -Eq pattern out of verify-guard-parity.sh's own
    SYNC BINDING check, rather than hardcoding a copy of it here. A
    hardcoded literal doesn't change when the production pattern does --
    this test would keep passing (or failing) against a stale definition
    while a real regression in the production check goes undetected.
    Reading it from the source means drift between the two is impossible
    by construction: there is only one pattern, extracted at test time."""
    text = VERIFY.read_text(encoding="utf-8")
    match = re.search(
        r"grep -Eq '(\^\[\[:space:\]\].*guard-sync-manifest\\\.sh)'",
        text,
    )
    assert match, (
        "could not find the SYNC BINDING grep pattern in "
        f"{VERIFY} -- verify-guard-parity.sh's check may have been "
        "rewritten in a way this extraction no longer matches"
    )
    return match.group(1)


_SYNC_BINDING_PATTERN = _extract_sync_binding_pattern()


def _run_sync_binding_check(sync_script: Path) -> subprocess.CompletedProcess[str]:
    """Same grep as verify-guard-parity.sh SYNC BINDING check."""
    if sys.platform == "win32":
        # The MSYS runtime strips backslashes from Windows command lines, which
        # turns the pattern's escaped dot into a wildcard; read it from a file.
        with tempfile.TemporaryDirectory() as tmp:
            pattern_file = Path(tmp) / "pattern.txt"
            pattern_file.write_bytes(_SYNC_BINDING_PATTERN.encode("utf-8"))
            return subprocess.run(
                ["grep", "-Eq", "-f", str(pattern_file), str(sync_script)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
    return subprocess.run(
        ["grep", "-Eq", _SYNC_BINDING_PATTERN, str(sync_script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _bash_array(name: str) -> list[str]:
    result = subprocess.run(
        [
            "bash",
            "-c",
            f'source "$1" && printf "%s\\n" "${{{name}[@]}}"',
            "_",
            str(MANIFEST),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


@pytest.mark.unit
def test_manifest_files_exist_on_disk() -> None:
    """Every manifest path exists in the canonical checkout."""
    all_paths = _bash_array("GUARD_PARITY_ROOT_REQUIRED")
    missing = [rel for rel in all_paths if not (ROOT / rel).is_file()]
    assert not missing, f"manifest lists missing files: {missing}"


@pytest.mark.unit
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX executable bits are not represented on Windows checkouts",
)
def test_cursor_executables_are_executable_in_canonical_source() -> None:
    """Cursor guard executables in the manifest are executable on disk."""
    helpers = _bash_array("GUARD_SYNC_CURSOR_EXECUTABLES")
    non_executable = [
        f"scripts/cursor/{rel}"
        for rel in helpers
        if not (ROOT / "scripts/cursor" / rel).stat().st_mode & 0o111
    ]
    assert not non_executable, f"cursor helpers must match their synced executable mode: {non_executable}"


@pytest.mark.unit
def test_parity_required_expands_in_bash() -> None:
    """Every unconditional sync destination participates in root-level parity."""
    parity = set(_bash_array("GUARD_PARITY_ROOT_REQUIRED"))
    expected = {
        *(f"scripts/git/{rel}" for rel in _bash_array("GUARD_SYNC_EXECUTABLES")),
        *(f"scripts/git/{rel}" for rel in _bash_array("GUARD_SYNC_DATA_FILES")),
        *(f"scripts/cursor/{rel}" for rel in _bash_array("GUARD_SYNC_CURSOR_EXECUTABLES")),
        *(f".cursor/commands/{rel}" for rel in _bash_array("GUARD_SYNC_CURSOR_COMMANDS")),
        *(f".cursor/rules/{rel}" for rel in _bash_array("GUARD_SYNC_CURSOR_RULES")),
    }
    assert parity == expected


@pytest.mark.unit
def test_sync_and_verify_source_manifest() -> None:
    pattern = r'^\s*(source|\.)\s+.*guard-sync-manifest\.sh'
    for script in (SYNC, VERIFY):
        body = script.read_text(encoding="utf-8")
        assert re.search(pattern, body, re.MULTILINE), (
            f"{script.name} must source guard-sync-manifest.sh via an uncommented command"
        )


@pytest.mark.unit
def test_verify_rejects_comment_only_manifest_reference(tmp_path: Path) -> None:
    """Comment-only 'source guard-sync-manifest.sh' must not satisfy the binding check."""
    fake_sync = tmp_path / "sync-attribution-guard-scripts.sh"
    fake_sync.write_text(
        "# source guard-sync-manifest.sh\n",
        encoding="utf-8",
    )
    fake_result = _run_sync_binding_check(fake_sync)
    assert fake_result.returncode != 0, (
        "production binding grep must reject comment-only manifest reference"
    )
    real_result = _run_sync_binding_check(SYNC)
    assert real_result.returncode == 0, (
        "canonical sync-attribution-guard-scripts.sh must satisfy binding check"
    )


@pytest.mark.unit
def test_verify_guard_parity_passes_in_canonical_repo() -> None:
    result = subprocess.run(
        ["bash", str(VERIFY)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.unit
def test_verify_guard_parity_reports_cursor_helper_drift(tmp_path: Path) -> None:
    """Parity verification reports drift in a mirrored Cursor helper."""
    target = tmp_path / "downstream"
    target.mkdir()
    drifted = target / "scripts/cursor/append-pr-body.sh"
    drifted.parent.mkdir(parents=True)
    drifted.write_text("# divergent\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(VERIFY), str(target)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode != 0
    assert "scripts/cursor/append-pr-body.sh DRIFTED" in result.stdout


def test_markdown_lint_gate_is_a_synced_guard_executable() -> None:
    """The pre-commit markdown gate is byte-synced like every other guard script.

    It was once listed only in a header comment ("same script in both repos"),
    so the copies drifted within a day with nothing to notice. Being in the
    manifest puts it under sync-attribution-guard-scripts.sh and parity checks.
    """
    assert "check_markdown_lint.sh" in _bash_array("GUARD_SYNC_EXECUTABLES")


def test_markdown_lint_gate_passes_awkward_staged_paths_through_unquoted(
    tmp_path: Path,
) -> None:
    """Spaces and non-ASCII names reach the linter exactly, not C-quoted.

    Without NUL-delimited output git quotes such paths ("caf\\303\\251.md"), so
    the linter would be handed a name that does not exist. A stub linter records
    its argv so the test does not depend on markdownlint being installed.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {"PATH": str(tmp_path / "bin") + ":/usr/bin:/bin", "HOME": str(tmp_path)}
    if sys.platform == "win32":
        # Git for Windows keeps git outside /usr/bin, so expose it explicitly.
        git_exe = shutil.which("git")
        assert git_exe is not None, "git executable not found"
        env["PATH"] = os.pathsep.join(
            (str(tmp_path / "bin"), str(Path(git_exe).parent), os.environ["PATH"])
        )
        env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")
    (tmp_path / "bin").mkdir()
    record = tmp_path / "argv.txt"
    stub = tmp_path / "bin" / "markdownlint-cli2"
    stub.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{record}"\n', encoding="utf-8")
    stub.chmod(0o755)

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, env=env)

    git("init", "-q")
    awkward = ["café notes.md", "plain.md"]
    for name in awkward:
        (repo / name).write_text("# t\n", encoding="utf-8")
    git("add", "--", *awkward)

    result = subprocess.run(
        ["bash", str(GIT / "check_markdown_lint.sh")],
        cwd=repo, capture_output=True, text=True, env=env, encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    assert sorted(record.read_text(encoding="utf-8").splitlines()) == sorted(awkward)


def test_markdown_lint_gate_is_silent_when_no_markdown_is_staged(tmp_path: Path) -> None:
    """Nothing staged means exit 0 without invoking any linter (bash 3.2 safe)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
    result = subprocess.run(
        ["bash", str(GIT / "check_markdown_lint.sh")],
        cwd=repo, capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
