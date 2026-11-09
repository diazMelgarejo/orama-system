"""Tests for lan_peer_pulse: a read-only both-direction health pulse that never sends anything."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts"))

import lan_peer_pulse as pulse  # noqa: E402

START_PS1 = ROOT / "platform" / "windows" / "start.ps1"
ALL_PASS = {"checks": [{"name": n, "status": "PASS"} for n in ("portal-health", "portal-status", "ws-peer", "peer-lmstudio")]}
GREEN = {"ok": True, "checks": {"portal-health": "PASS"}}
RED = {"ok": False, "checks": {"portal-health": "FAIL"}}
NO_DROPS = {"status": "none", "mac_drops": 0, "new": [], "newest": None}


def test_interval_defaults_to_thirty_minutes_and_has_a_floor() -> None:
    """Default 30 minutes; garbage falls back to the default; values under five minutes are raised to 300."""
    assert pulse.interval_seconds({}) == 1800
    assert pulse.interval_seconds({"LAN_PEER_PULSE_SECONDS": "abc"}) == 1800
    assert pulse.interval_seconds({"LAN_PEER_PULSE_SECONDS": "5"}) == 300
    assert pulse.interval_seconds({"LAN_PEER_PULSE_SECONDS": "3600"}) == 3600


def test_probe_uses_the_https_port_only_when_peer_https_is_enabled() -> None:
    """https on means --portal-port with the configured port (default 8443, bad values default); off adds nothing."""
    assert "--portal-port" not in pulse.probe_command({})
    cmd = pulse.probe_command({"PEER_PORTAL_TLS_ENABLED": "1"})
    assert cmd[cmd.index("--portal-port") + 1] == "8443"
    cmd = pulse.probe_command({"PEER_PORTAL_TLS_ENABLED": "1", "PEER_PORTAL_TLS_PORT": "9443"})
    assert cmd[cmd.index("--portal-port") + 1] == "9443"
    cmd = pulse.probe_command({"PEER_PORTAL_TLS_ENABLED": "1", "PEER_PORTAL_TLS_PORT": "99999"})
    assert cmd[cmd.index("--portal-port") + 1] == "8443"


def test_summary_needs_health_status_and_websocket_to_pass() -> None:
    """The LM Studio check does not decide the link; losing any of the three required checks does."""
    assert pulse.summarize_probe(ALL_PASS)["ok"] is True
    broken = {"checks": [{"name": "portal-health", "status": "PASS"}, {"name": "portal-status", "status": "FAIL"},
                         {"name": "ws-peer", "status": "PASS"}]}
    assert pulse.summarize_probe(broken)["ok"] is False
    assert pulse.summarize_probe({})["ok"] is False


def test_summary_keeps_only_names_and_status_words() -> None:
    """No detail text (which can hold addresses) is carried into the summary."""
    result = {"checks": [{"name": "portal-health", "status": "FAIL", "detail": "https://203.0.113.5:8443/health refused"}]}
    assert "203.0.113.5" not in json.dumps(pulse.summarize_probe(result))


def test_first_pulse_logs_once_and_a_transition_logs_again() -> None:
    """First pulse logs its status; staying the same logs nothing; green to red and red to green each log."""
    state, lines = pulse.update_state({}, GREEN, NO_DROPS, 100.0)
    assert lines == ["win_to_mac ok (first pulse)"]
    state, lines = pulse.update_state(state, GREEN, NO_DROPS, 200.0)
    assert lines == []
    state, lines = pulse.update_state(state, RED, NO_DROPS, 300.0)
    assert lines == ["win_to_mac FAILED: probe no longer passes"] and state["win_to_mac"]["consecutive_failures"] == 1
    state, lines = pulse.update_state(state, RED, NO_DROPS, 400.0)
    assert lines == [] and state["win_to_mac"]["consecutive_failures"] == 2
    state, lines = pulse.update_state(state, GREEN, NO_DROPS, 500.0)
    assert lines == ["win_to_mac recovered: probe passes again"] and state["win_to_mac"]["consecutive_failures"] == 0
    assert state["win_to_mac"]["last_ok_utc"] == 500.0


def test_last_ok_time_survives_a_failure() -> None:
    """A red pulse keeps the time of the last green one."""
    state, _ = pulse.update_state({}, GREEN, NO_DROPS, 100.0)
    state, _ = pulse.update_state(state, RED, NO_DROPS, 200.0)
    assert state["win_to_mac"]["last_ok_utc"] == 100.0


def test_new_mac_drops_and_integrity_failures_are_reported() -> None:
    """New drops are counted and logged; an integrity failure is logged once."""
    inbox = {"status": "new", "mac_drops": 3, "new": ["a.md", "b.md"], "newest": {"received_at": 150}}
    state, lines = pulse.update_state({}, GREEN, inbox, 200.0)
    assert "mac_to_win: 2 new Mac drop(s) arrived" in lines
    assert state["mac_to_win"]["newest_received_utc"] == 150
    bad = {"status": "integrity-fail", "mac_drops": 3, "new": [], "newest": None}
    state, lines = pulse.update_state(state, GREEN, bad, 300.0)
    assert "mac_to_win: a Mac drop failed its integrity check" in lines
    state, lines = pulse.update_state(state, GREEN, bad, 400.0)
    assert not any("integrity" in line for line in lines)


def test_a_cycle_runs_only_the_two_read_only_scripts_and_writes_state(tmp_path, monkeypatch) -> None:
    """One cycle invokes the probe and the inbox check and nothing else (no drop, no flush), then saves the state."""
    seen: list[list[str]] = []

    def fake_run(cmd):
        """Record the command and return a canned probe or inbox result."""
        seen.append(cmd)
        return ALL_PASS if "probe_lan_peer.py" in " ".join(cmd) else NO_DROPS

    monkeypatch.setattr(pulse, "_run_json", fake_run)
    state_path = tmp_path / "pulse.json"
    state, _ = pulse.run_cycle(state_path, env={}, now=1.0)
    names = [Path(c[3]).name for c in seen]
    assert names == ["probe_lan_peer.py", "lan_peer_inbox_check.py"]
    assert json.loads(state_path.read_text(encoding="utf-8"))["win_to_mac"]["ok"] is True
    assert not list(tmp_path.glob("*.tmp"))


def test_the_pulse_source_never_sends_or_flushes() -> None:
    """The script imports no network client and names only the two read-only scripts it may run."""
    import ast

    source = (ROOT / "bin/orama-system/skills/hermes-harness/scripts/lan_peer_pulse.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not imported & {"urllib", "socket", "http", "ssl", "requests"}
    scripts = {s for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
               for s in re.findall(r"[\w-]+\.py", n.value)}
    assert scripts <= {"probe_lan_peer.py", "lan_peer_inbox_check.py"}


def test_start_ps1_autostarts_the_pulse_with_lan_peer_and_stops_it_by_pid_file() -> None:
    """start.ps1 spawns the pulse detached inside the --lan-peer block and --stop kills it only after a command-line match."""
    text = START_PS1.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    assert "lan_peer_pulse.py" in text
    assert text.index("lan-peer-pulse started detached") > text.index("lm-link-watch started detached")
    assert text.index("# ── LAN peer pulse autostart") < text.index("if (-not $NoOpen) {")
    assert "Life-PidMatches $recorded '^pythonw?[0-9.]*$' 'lan_peer_pulse'" in text
    assert "-Cmd @($UsPython, '-X', 'utf8', $PulseScript)" in text


@pytest.mark.parametrize("name", ["lan_peer_pulse.py"])
def test_the_pulse_script_is_documented(name: str) -> None:
    """The module has a docstring that states it is read-only."""
    assert "never sends a message" in pulse.__doc__
