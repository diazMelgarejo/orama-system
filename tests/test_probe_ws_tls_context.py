"""WebSocket peer check must use the per-stack peer_tls context."""
from __future__ import annotations

import ssl
import sys
import types
from pathlib import Path

import pytest

pytest.importorskip("cryptography", reason="cryptography needed to mint throwaway test certs")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import peer_tls_fixtures as fx  # noqa: E402

import peer_tls  # noqa: E402
import probe_lan_peer as probe  # noqa: E402

PEER = "192.0.2.10"  # TEST-NET-1


@pytest.fixture
def captured(monkeypatch):
    for var in ("PEER_CA_FILE", "PEER_PINNED_FINGERPRINTS", "SSL_CERT_FILE"):
        monkeypatch.delenv(var, raising=False)
    peer_tls.clear_cache()
    calls: list[tuple[str, dict]] = []

    class _WS:
        async def send(self, _msg):
            return None

        async def recv(self):
            return '{"type": "probe-ack"}'

    class _Conn:
        def __init__(self, url, **kw):
            calls.append((url, kw))

        async def __aenter__(self):
            return _WS()

        async def __aexit__(self, *exc):
            return False

    mod = types.ModuleType("websockets")
    mod.connect = _Conn
    monkeypatch.setitem(sys.modules, "websockets", mod)
    return calls


def test_peer_ca_file_context_is_passed_to_wss(captured, monkeypatch, tmp_path):
    ca = fx.make_ca()
    monkeypatch.setenv("PEER_CA_FILE", str(fx.write_pem(tmp_path / "ca.pem", ca[1])))
    chk = probe.check_ws_peer(PEER, 8002, ["synthetic-token"], timeout=2)
    assert chk.status == probe.Status.PASS
    url, kw = captured[0]
    assert url.startswith("wss://")
    assert isinstance(kw["ssl"], ssl.SSLContext)
    assert kw["ssl"].verify_mode == ssl.CERT_REQUIRED and kw["ssl"].check_hostname


def test_no_peer_trust_leaves_default_context_so_ssl_cert_file_applies(captured, monkeypatch, tmp_path):
    monkeypatch.setenv("SSL_CERT_FILE", str(fx.write_pem(tmp_path / "roots.pem", fx.make_ca()[1])))
    chk = probe.check_ws_peer(PEER, 8002, ["synthetic-token"], timeout=2)
    assert chk.status == probe.Status.PASS
    url, kw = captured[0]
    # No per-stack override: the library's default verified context is used,
    # which honours SSL_CERT_FILE.
    assert url.startswith("wss://") and "ssl" not in kw


def test_trust_failure_fails_closed_without_connecting(captured, monkeypatch, tmp_path):
    monkeypatch.setenv("PEER_CA_FILE", str(tmp_path / "missing.pem"))
    chk = probe.check_ws_peer(PEER, 8002, ["synthetic-token"], timeout=2)
    assert chk.status == probe.Status.FAIL and "token not sent" in chk.detail
    assert captured == []


def test_websocket_kwargs_selection(monkeypatch, tmp_path):
    monkeypatch.delenv("PEER_PINNED_FINGERPRINTS", raising=False)
    monkeypatch.delenv("PEER_CA_FILE", raising=False)
    peer_tls.clear_cache()
    assert peer_tls.websocket_kwargs(f"ws://{PEER}:8002/ws/portal-peer") == {}
    assert peer_tls.websocket_kwargs(f"wss://{PEER}:8002/ws/portal-peer") == {}
    monkeypatch.setenv("PEER_CA_FILE", str(fx.write_pem(tmp_path / "ca.pem", fx.make_ca()[1])))
    assert peer_tls.websocket_kwargs(f"ws://{PEER}:8002/x") == {}
    assert isinstance(peer_tls.websocket_kwargs(f"wss://{PEER}:8002/x")["ssl"], ssl.SSLContext)
