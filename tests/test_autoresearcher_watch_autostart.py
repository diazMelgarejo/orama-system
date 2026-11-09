"""Tests that start.ps1 starts and stops the AutoResearcher fallback watcher itself (CLINE-PICKUP-07).

Before this change the watcher was launched by hand through WMI with its identity and state-directory
environment set; ``start.ps1`` neither started nor stopped it, so a restart silently dropped it.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
START_PS1 = ROOT / "platform" / "windows" / "start.ps1"
WATCH_PS1 = ROOT / "scripts" / "cline_autoresearcher_watch.ps1"


def _start_text() -> str:
    """start.ps1 text with LF line endings and the BOM removed."""
    return START_PS1.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def test_start_ps1_autostarts_the_watcher_in_the_lan_peer_block_after_the_pulse() -> None:
    """The watcher block sits inside the --lan-peer section, after the pulse block and before the browser open."""
    text = _start_text()
    assert "# ── AutoResearcher fallback watcher autostart" in text
    assert text.index("# ── AutoResearcher fallback watcher autostart") > text.index("# ── LAN peer pulse autostart")
    assert text.index("# ── AutoResearcher fallback watcher autostart") < text.index("if (-not $NoOpen) {")
    assert "autoresearcher_watch.pid" in text and "autoresearcher-watch.log" in text


def test_the_watcher_is_spawned_detached_with_identity_and_state_dir_environment() -> None:
    """Life-Spawn carries PT_AGENT_ID (default win-researcher), UTF-8 and an explicit PT_STATE_DIR for the linked worktree."""
    text = _start_text()
    block = text[text.index("# ── AutoResearcher fallback watcher autostart"):text.index("if (-not $NoOpen) {")]
    assert "Life-Spawn" in block and "cline_autoresearcher_watch.ps1" in block
    assert "'-RepoRoot', $RepoRoot" in block and "'-UsPython', $UsPython" in block and "'-LogDir', $LogDir" in block
    assert "PT_AGENT_ID" in block and "win-researcher" in block
    assert "PT_STATE_DIR" in block and "PYTHONUTF8" in block


def test_the_watcher_can_be_disabled_and_is_idempotent() -> None:
    """AUTORESEARCHER_WATCH_DISABLE=1 skips it, and a running watcher (matched by command line) is not started twice."""
    block = _start_text()
    block = block[block.index("# ── AutoResearcher fallback watcher autostart"):block.index("if (-not $NoOpen) {")]
    assert "AUTORESEARCHER_WATCH_DISABLE" in block
    assert "Life-PidMatches $arPid '^(powershell|pwsh)$' 'cline_autoresearcher_watch'" in block
    assert "already running" in block


def test_stop_kills_the_watcher_only_after_a_command_line_match() -> None:
    """--stop recognises the watcher pid file and verifies the command line, never the process name alone."""
    text = _start_text()
    assert re.search(r"BaseName -eq 'autoresearcher_watch'\)\s*\{\s*#[^\n]*\n\s*\$owned = Life-PidMatches \$recorded '\^\(powershell\|pwsh\)\$' 'cline_autoresearcher_watch'", text)


def test_the_watcher_script_documents_that_start_ps1_launches_it_with_named_arguments() -> None:
    """The watcher header matches how start.ps1 really calls it (named parameters)."""
    header = WATCH_PS1.read_text(encoding="utf-8-sig")[:900]
    assert "-RepoRoot" in header and "-UsPython" in header and "-LogDir" in header


@pytest.mark.skipif(shutil.which("powershell.exe") is None, reason="Windows PowerShell is needed to parse the script")
def test_start_ps1_still_parses_as_powershell() -> None:
    """The edited launcher is syntactically valid Windows PowerShell 5.1."""
    cmd = ("$e=$null;$t=$null;[void][System.Management.Automation.Language.Parser]::ParseFile("
           f"'{START_PS1}',[ref]$t,[ref]$e);if($e.Count){{$e|ForEach-Object{{$_.Message}};exit 1}}")
    done = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr
