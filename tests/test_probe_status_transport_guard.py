"""probe_lan_peer.run_checks must never send a bearer over plain http://.

Before this guard the authenticated /api/status check always used http://,
so running the probe against a TLS-only peer port sent the control-plane
token in cleartext.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts" / "probe_lan_peer.py"
)
PEER = "192.0.2.10"


@pytest.fixture
def peer_mod(monkeypatch):
    """Load a fresh copy of probe_lan_peer with the WebSocket check stubbed to skip."""
    spec = importlib.util.spec_from_file_location("probe_lan_peer_guard", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(
        mod, "check_ws_peer",
        lambda peer_ip, portal_port, tokens, **kw: mod.Check("ws-peer", mod.Status.SKIP, ""),
    )
    return mod


def _recorder(calls):
    """Return a fake http_get that records (url, token) calls and answers successfully."""
    def fake_get(url: str, token: str = "", timeout: int = 8):
        """Record the call and answer health, models or a generic success."""
        calls.append((url, token))
        if url.endswith("/health"):
            return 200, '{"status":"ok"}'
        if url.endswith("/v1/models"):
            return 200, json.dumps({"data": []})
        return 200, "{}"
    return fake_get


def test_token_never_sent_over_http(peer_mod, monkeypatch):
    """Over plain http the status check fails with SECURITY_STOP and no token is sent."""
    monkeypatch.delenv("PEER_PORTAL_TLS_ENABLED", raising=False)
    calls: list = []
    monkeypatch.setattr(peer_mod, "http_get", _recorder(calls))
    checks = peer_mod.run_checks(PEER, 1234, 8443, ["synthetic-token"])
    status = {c.name: c for c in checks}["portal-status"]
    assert status.status == peer_mod.Status.FAIL
    assert "SECURITY_STOP" in status.detail
    assert all(token == "" for _url, token in calls), calls
    assert not any("/api/status" in url for url, _ in calls)


def test_token_sent_only_over_https_when_tls_enabled(peer_mod, monkeypatch):
    """With TLS enabled tokens are sent only to https URLs and status passes."""
    monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
    calls: list = []
    monkeypatch.setattr(peer_mod, "http_get", _recorder(calls))
    checks = peer_mod.run_checks(PEER, 1234, 8443, ["synthetic-token"])
    assert {c.name: c for c in checks}["portal-status"].status == peer_mod.Status.PASS
    sent = [url for url, token in calls if token]
    assert sent and all(url.startswith("https://") for url in sent)
    assert any(url == f"https://{PEER}:8443/health" for url, _ in calls)


def test_no_tokens_still_skips_status(peer_mod, monkeypatch):
    """With no tokens the status check is skipped."""
    monkeypatch.delenv("PEER_PORTAL_TLS_ENABLED", raising=False)
    calls: list = []
    monkeypatch.setattr(peer_mod, "http_get", _recorder(calls))
    checks = peer_mod.run_checks(PEER, 1234, 8002, [])
    assert {c.name: c for c in checks}["portal-status"].status == peer_mod.Status.SKIP
