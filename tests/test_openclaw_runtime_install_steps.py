"""First-run step 0.9 calls the Perpetua-Tools runtime script; the watcher alerts on drift without fixing it."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRST_RUN = ROOT / "bin/orama-system/scripts/first-run-install.sh"
DOC = ROOT / "bin/orama-system/references/first-run-install.md"
WATCH = ROOT / "scripts/install_openclaw_runtime_watch.sh"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_both_scripts_parse_under_the_macos_system_bash() -> None:
    for script in (FIRST_RUN, WATCH):
        assert subprocess.run(["/bin/bash", "-n", str(script)], capture_output=True).returncode == 0, script


def test_first_run_has_step_0_9_in_both_check_and_install_modes() -> None:
    text = _text(FIRST_RUN)
    assert "check_openclaw_runtime()" in text and "run_openclaw_runtime()" in text
    assert "check_openclaw_runtime || true" in text and "run_openclaw_runtime || true" in text


def test_first_run_never_triggers_the_destructive_fresh_gateway_step() -> None:
    """Moving ~/.openclaw aside and onboarding fresh is an explicit operator action, never part of first-run."""
    assert "--fresh-gateway" not in _text(FIRST_RUN)


def test_first_run_apply_respects_dry_run_and_an_opt_out() -> None:
    body = _text(FIRST_RUN).split("run_openclaw_runtime() {", 1)[1].split("\n}\n", 1)[0]
    assert "DRY_RUN" in body and "OPENCLAW_RUNTIME" in body and "uname" in body


def test_the_step_is_documented_in_the_table_and_a_section() -> None:
    doc = _text(DOC)
    assert "| 0.9 |" in doc and "## 0.9 OpenClaw runtime" in doc
    assert "install-openclaw-runtime.sh" in doc and "--fresh-gateway" in doc, "the manual step must be documented"


def _stub_launchctl(bin_dir: Path) -> Path:
    log = bin_dir / "launchctl.calls"
    stub = bin_dir / "launchctl"
    stub.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\n', encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    return log


def test_the_watcher_installs_an_alert_only_wrapper_and_a_timer_agent(tmp_path: Path) -> None:
    home, bin_dir = tmp_path / "home", tmp_path / "bin"
    home.mkdir()
    bin_dir.mkdir()
    calls = _stub_launchctl(bin_dir)
    env = {"HOME": str(home), "PATH": f"{bin_dir}:/usr/bin:/bin", "PERPETUA_TOOLS_ROOT": "/pt"}
    done = subprocess.run(["bash", str(WATCH)], capture_output=True, text=True, env={**os.environ, **env})
    assert done.returncode == 0, done.stderr
    plist = (home / "Library/LaunchAgents/com.orama.openclaw-runtime-watch.plist").read_text(encoding="utf-8")
    assert "<key>StartInterval</key>" in plist and "<key>KeepAlive</key>" not in plist
    wrapper = (home / ".local/state/openclaw-runtime/watch-run.sh").read_text(encoding="utf-8")
    assert "perpetua_tools.openclaw_runtime --check --json" in wrapper and "osascript" in wrapper
    assert "--apply" not in wrapper, "the watcher alerts; it never rewrites the service"
    assert "load" in calls.read_text(encoding="utf-8")


def test_the_watcher_uninstall_removes_only_its_own_agent(tmp_path: Path) -> None:
    home, bin_dir = tmp_path / "home", tmp_path / "bin"
    (home / "Library/LaunchAgents").mkdir(parents=True)
    bin_dir.mkdir()
    _stub_launchctl(bin_dir)
    other = home / "Library/LaunchAgents/com.orama.network-watch.plist"
    other.write_text("keep", encoding="utf-8")
    env = {**os.environ, "HOME": str(home), "PATH": f"{bin_dir}:/usr/bin:/bin", "PERPETUA_TOOLS_ROOT": "/pt"}
    subprocess.run(["bash", str(WATCH)], capture_output=True, text=True, env=env, check=True)
    subprocess.run(["bash", str(WATCH), "--uninstall"], capture_output=True, text=True, env=env, check=True)
    assert not (home / "Library/LaunchAgents/com.orama.openclaw-runtime-watch.plist").exists()
    assert other.read_text(encoding="utf-8") == "keep"


CARD = ROOT / "bin/orama-system/references/openclaw-staged-restore-and-recovery.md"


def test_the_recovery_card_exists_and_covers_install_restore_and_rollback() -> None:
    text = _text(CARD)
    for heading in (
        "## Preconditions",
        "## Fresh install procedure",
        "## Staged restore order",
        "## Credential handling",
        "## Backup and recovery",
        "## Verification after each stage",
    ):
        assert heading in text, heading
    for must in ("bootout", "Trash", "dry-run", "shell import", "length and hash"):
        assert must in text, must


def test_the_recovery_card_is_portable_and_linked_from_step_0_9() -> None:
    import re

    text = _text(CARD)
    assert "/Users/" not in text, "no workstation paths in tracked files"
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", text), "no address literals in tracked files"
    assert all(len(line) <= 100 for line in text.splitlines()), "markdownlint line length"
    assert "openclaw-staged-restore-and-recovery.md" in _text(DOC), "step 0.9 must link the card"
