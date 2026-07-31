"""Regression tests for scripts/git/sync-attribution-guard-scripts.sh's
atomic_append_snippet() -- specifically the fix for a brace group whose
exit status only reflected the LAST command, silently missing a failed
`cat "$dest"` as long as the snippet read still succeeded afterward.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/git/sync-attribution-guard-scripts.sh"

pytestmark = pytest.mark.unit


def _extract_function(name: str) -> str:
    """Pull just one function's definition out of the script by brace
    matching, rather than sourcing the whole file -- the script does
    real argument validation and work at its top level (not guarded
    behind a `if [[ "$0" == "${BASH_SOURCE[0]}" ]]`-style check), so
    sourcing it directly runs the sync process itself, not just defines
    functions."""
    text = SCRIPT.read_text(encoding="utf-8")
    start = text.index(f"{name}() {{")
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1
    raise AssertionError(f"could not find end of function {name}")


def _run_atomic_append_snippet(dest: Path, mode: str, snippet: Path) -> subprocess.CompletedProcess[str]:
    func_src = _extract_function("atomic_append_snippet")
    wrapper = f'set -euo pipefail\n{func_src}\natomic_append_snippet "{dest}" "{mode}" "{snippet}"\n'
    return subprocess.run(["bash", "-c", wrapper], capture_output=True, text=True)


def test_append_snippet_creates_new_dest_when_missing(tmp_path: Path) -> None:
    dest = tmp_path / "new-file.txt"
    snippet = tmp_path / "snippet.txt"
    snippet.write_text("snippet content\n", encoding="utf-8")

    result = _run_atomic_append_snippet(dest, "0644", snippet)

    assert result.returncode == 0, result.stderr
    assert dest.is_file()
    assert "snippet content" in dest.read_text(encoding="utf-8")


def test_append_snippet_preserves_existing_dest_content(tmp_path: Path) -> None:
    dest = tmp_path / "existing.txt"
    dest.write_text("original content\n", encoding="utf-8")
    snippet = tmp_path / "snippet.txt"
    snippet.write_text("appended content\n", encoding="utf-8")

    result = _run_atomic_append_snippet(dest, "0644", snippet)

    assert result.returncode == 0, result.stderr
    final = dest.read_text(encoding="utf-8")
    assert "original content" in final
    assert "appended content" in final


def test_append_snippet_fails_closed_on_unreadable_dest(tmp_path: Path) -> None:
    """The specific bug this fixes: a dest that exists but can't be read
    must fail loudly, not silently produce a dest missing its original
    content while still reporting success. Skipped when running as root,
    since chmod 0o000 doesn't block root's own reads -- this sandbox
    happens to run as root; CI's actual runner does not, where this test
    genuinely exercises the fix."""
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("running as root -- chmod 0o000 does not block root's reads")

    dest = tmp_path / "unreadable.txt"
    dest.write_text("content that must not be lost\n", encoding="utf-8")
    dest.chmod(0o000)
    snippet = tmp_path / "snippet.txt"
    snippet.write_text("new content\n", encoding="utf-8")

    result = _run_atomic_append_snippet(dest, "0644", snippet)

    dest.chmod(0o644)  # restore for cleanup regardless of outcome
    assert result.returncode != 0, "must fail closed, not silently truncate dest"
    assert "failed reading" in result.stderr
    assert "content that must not be lost" in dest.read_text(encoding="utf-8"), (
        "original content must survive a failed append attempt"
    )
