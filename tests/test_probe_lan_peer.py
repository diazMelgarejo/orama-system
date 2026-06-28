"""Tests for probe_lan_peer.py (offline / mocked)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "bin"
    / "orama-system"
    / "skills"
    / "hermes-harness"
    / "scripts"
    / "probe_lan_peer.py"
)


@pytest.fixture
def peer_mod(monkeypatch):
    spec = importlib.util.spec_from_file_location("probe_lan_peer", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


def test_peer_from_discovery_mac_role(peer_mod):
    discovery = {"endpoints": {"win": {"ip": "10.0.0.50", "port": 1234}}}
    ip, port = peer_mod.peer_from_discovery(discovery, "mac")
    assert ip == "10.0.0.50"
    assert port == 1234


def test_run_checks_lmstudio_pass(peer_mod, monkeypatch):
    def fake_get(url: str, token: str = "", timeout: int = 8):
        if url.endswith("/health"):
            return 200, '{"status":"ok"}'
        if url.endswith("/v1/models"):
            return 200, json.dumps({"data": [{"id": "m1"}]})
        return 404, "nope"

    monkeypatch.setattr(peer_mod, "http_get", fake_get)
    checks = peer_mod.run_checks("10.0.0.50", 1234, 8002, token="")
    by_name = {c.name: c.status for c in checks}
    assert by_name["portal-health"] == peer_mod.Status.PASS
    assert by_name["peer-lmstudio"] == peer_mod.Status.PASS
    assert by_name["portal-status"] == peer_mod.Status.SKIP


def test_main_json_exit_zero_when_lmstudio_ok(peer_mod, monkeypatch, capsys, tmp_path):
    disc = tmp_path / "last_discovery.json"
    disc.write_text(
        json.dumps({"endpoints": {"win": {"ip": "10.0.0.50", "port": 1234}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(peer_mod, "discovery_path", lambda: disc)
    monkeypatch.setattr(peer_mod, "local_role", lambda: "mac")

    def fake_get(url: str, token: str = "", timeout: int = 8):
        if "/health" in url:
            return 200, "ok"
        return 200, json.dumps({"data": []})

    monkeypatch.setattr(peer_mod, "http_get", fake_get)
    rc = peer_mod.main(["--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["peer_ip"] == "10.0.0.50"
