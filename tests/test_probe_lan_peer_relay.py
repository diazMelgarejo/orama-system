"""Offline unit tests for probe_lan_peer.py's --relay client (mother plan §4.4/§5).

Complements tests/test_fleet_topology_api.py's server-side coverage of
POST /api/peer-relay-probe: these tests exercise the CLIENT half (token
retry on 401, exit-code contract, transport-failure handling) with
http_post_json mocked -- no network, no portal process.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts"
    / "probe_lan_peer.py"
)
_spec = importlib.util.spec_from_file_location("probe_lan_peer", _SCRIPT)
probe_lan_peer = importlib.util.module_from_spec(_spec)
sys.modules["probe_lan_peer"] = probe_lan_peer
_spec.loader.exec_module(probe_lan_peer)  # type: ignore[union-attr]


def _ok_body(reachable: bool = True) -> str:
    return json.dumps(
        {
            "reachable": reachable,
            "ip": "192.168.8.153",
            "models": ["gemma-4-26b-a4b-it-nvfp4"] if reachable else [],
            "relay_path": ["B→C"] if reachable else [],
        }
    )


def test_relay_probe_target_up(monkeypatch):
    monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
    calls = []

    def fake_post(url, payload, token="", timeout=8):
        calls.append((url, payload, token))
        return 200, _ok_body(True)

    monkeypatch.setattr(probe_lan_peer, "http_post_json", fake_post)
    code, result = probe_lan_peer.relay_probe(
        "10.0.0.2", 8002, "192.168.8.153:1234", 8002, ["tok-a"]
    )
    assert code == 0
    assert result["reachable"] is True
    assert result["relay_via"] == "10.0.0.2:8002"
    assert calls[0][0] == "https://10.0.0.2:8002/api/peer-relay-probe"
    assert calls[0][1] == {"target_ip": "192.168.8.153", "target_port": 1234}


def test_relay_probe_target_down_is_exit_1(monkeypatch):
    monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
    monkeypatch.setattr(
        probe_lan_peer, "http_post_json", lambda *a, **k: (200, _ok_body(False))
    )
    code, result = probe_lan_peer.relay_probe(
        "10.0.0.2", 8002, "192.168.8.153", 8002, ["tok"]
    )
    assert code == 1
    assert result["reachable"] is False


def test_relay_probe_retries_next_token_on_401(monkeypatch):
    monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
    seen_tokens = []

    def fake_post(url, payload, token="", timeout=8):
        seen_tokens.append(token)
        if token == "bad":
            return 401, "unauthorized"
        return 200, _ok_body(True)

    monkeypatch.setattr(probe_lan_peer, "http_post_json", fake_post)
    code, _ = probe_lan_peer.relay_probe(
        "10.0.0.2", 8002, "1.2.3.4", 8002, ["bad", "good"]
    )
    assert code == 0
    assert seen_tokens == ["bad", "good"]


def test_relay_probe_transport_failure_is_exit_2(monkeypatch):
    monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
    monkeypatch.setattr(
        probe_lan_peer, "http_post_json", lambda *a, **k: (-1, "connection refused")
    )
    code, result = probe_lan_peer.relay_probe(
        "10.0.0.2", 8002, "1.2.3.4", 8002, ["tok"]
    )
    assert code == 2
    assert result["error"] == "relay request failed"


def test_relay_probe_refuses_real_token_over_http(monkeypatch):
    """Regression: a real token candidate must never be attempted over
    plain http:// -- http_post_json must never even be called."""
    monkeypatch.delenv("PEER_PORTAL_TLS_ENABLED", raising=False)
    called = {"n": 0}

    def fake_post(url, payload, token="", timeout=8):
        called["n"] += 1
        raise AssertionError("http_post_json must never be called over unauthenticated transport")

    monkeypatch.setattr(probe_lan_peer, "http_post_json", fake_post)
    code, result = probe_lan_peer.relay_probe(
        "10.0.0.2", 8002, "1.2.3.4", 8002, ["real-token"]
    )
    assert code == 2
    assert "SECURITY_STOP" in result["error"]
    assert called["n"] == 0


def test_relay_probe_default_port_and_bad_input(monkeypatch):
    captured = {}

    def fake_post(url, payload, token="", timeout=8):
        captured.update(payload)
        return 200, _ok_body(True)

    monkeypatch.setattr(probe_lan_peer, "http_post_json", fake_post)
    code, _ = probe_lan_peer.relay_probe("10.0.0.2", 8002, "1.2.3.4", 8002, [])
    assert code == 0
    assert captured["target_port"] == 8002  # default applied when no :port given

    code, result = probe_lan_peer.relay_probe(
        "10.0.0.2", 8002, "1.2.3.4:notaport", 8002, []
    )
    assert code == 2
    assert "invalid --relay port" in result["error"]

    code, result = probe_lan_peer.relay_probe("10.0.0.2", 8002, ":1234", 8002, [])
    assert code == 2
    assert "empty --relay target IP" in result["error"]
