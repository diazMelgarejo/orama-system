"""Tests for Mac<->Windows co-orchestration session state."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts" / "lan_peer_session.py"


def _load_session():
    spec = importlib.util.spec_from_file_location("lan_peer_session_for_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_failure_threshold_enters_macos_only_then_cools_down(monkeypatch, tmp_path):
    session = _load_session()
    root = tmp_path / "lan_peer"
    monkeypatch.setattr(session, "lan_peer_state_dir", lambda: root)
    monkeypatch.setenv("LAN_PEER_MAX_FAILURES", "2")
    monkeypatch.setenv("LAN_PEER_DEGRADED_RETRY_SECONDS", "900")

    first = session.record_failure("first", now=1_000)
    assert first["mode"] == "co-orchestration"
    second = session.record_failure("second", now=1_010)

    assert second["mode"] == "macos-only"
    assert second["failure_count"] == 2
    assert second["next_retry_after"] == 1_910
    retry, cooled = session.should_retry(now=1_500)
    assert retry is False
    assert cooled["mode"] == "macos-only"


def test_retry_window_reopens_and_success_resumes(monkeypatch, tmp_path):
    session = _load_session()
    root = tmp_path / "lan_peer"
    monkeypatch.setattr(session, "lan_peer_state_dir", lambda: root)
    monkeypatch.setenv("LAN_PEER_MAX_FAILURES", "1")
    monkeypatch.setenv("LAN_PEER_DEGRADED_RETRY_SECONDS", "900")

    failed = session.record_failure("down", now=2_000)
    assert failed["mode"] == "macos-only"
    retry, reopened = session.should_retry(now=2_901)
    assert retry is True
    assert reopened["last_retry_at"] == 2_901
    assert reopened["next_retry_after"] == 3_801

    resumed = session.record_success(now=2_910)
    assert resumed["mode"] == "co-orchestration"
    assert resumed["failure_count"] == 0
    assert resumed["resumed_at"] == 2_910
    saved = json.loads((root / "co_orchestration_session.json").read_text(encoding="utf-8"))
    assert saved["mode"] == "co-orchestration"


def test_cli_persists_saveable_session_file(tmp_path):
    home = tmp_path / "home"
    env = {
        **os.environ,
        "HOME": str(home),
        "LAN_PEER_MAX_FAILURES": "1",
        "LAN_PEER_DEGRADED_RETRY_SECONDS": "900",
    }

    result = subprocess.run(
        ["python3", str(SCRIPT), "record-failure", "--error", "offline"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    state_file = Path(payload["state_file"])
    assert payload["mode"] == "macos-only"
    assert state_file == home / ".openclaw" / "state" / "lan_peer" / "co_orchestration_session.json"
    assert state_file.is_file()
