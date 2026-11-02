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
    """Stub the websockets module and clear trust variables; returns the list of (url, kwargs) connection calls."""
    for var in ("PEER_CA_FILE", "PEER_PINNED_FINGERPRINTS", "SSL_CERT_FILE"):
        monkeypatch.delenv(var, raising=False)
    peer_tls.clear_cache()
    calls: list[tuple[str, dict]] = []

    class _WS:
        """Fake WebSocket that acknowledges the probe."""
        async def send(self, _msg):
            """Accept and ignore the outgoing message."""
            return None

        async def recv(self):
            """Return a probe acknowledgement message."""
            return '{"type": "probe-ack"}'

    class _Conn:
        """Fake connection that records its URL and keyword arguments."""
        def __init__(self, url, **kw):
            """Record the connection URL and keyword arguments."""
            calls.append((url, kw))

        async def __aenter__(self):
            """Enter the connection context and return the fake WebSocket."""
            return _WS()

        async def __aexit__(self, *exc):
            """Leave the connection context without suppressing exceptions."""
            return False

    mod = types.ModuleType("websockets")
    mod.connect = _Conn
    monkeypatch.setitem(sys.modules, "websockets", mod)
    return calls


def test_peer_ca_file_context_is_passed_to_wss(captured, monkeypatch, tmp_path):
    """A configured CA file yields a verifying SSL context passed to the wss connection."""
    ca = fx.make_ca()
    monkeypatch.setenv("PEER_CA_FILE", str(fx.write_pem(tmp_path / "ca.pem", ca[1])))
    chk = probe.check_ws_peer(PEER, 8002, ["synthetic-token"], timeout=2)
    assert chk.status == probe.Status.PASS
    url, kw = captured[0]
    assert url.startswith("wss://")
    assert isinstance(kw["ssl"], ssl.SSLContext)
    assert kw["ssl"].verify_mode == ssl.CERT_REQUIRED and kw["ssl"].check_hostname


def test_no_peer_trust_leaves_default_context_so_ssl_cert_file_applies(captured, monkeypatch, tmp_path):
    """With no peer trust configured no ssl argument is passed, so the default context (and SSL_CERT_FILE) applies."""
    monkeypatch.setenv("SSL_CERT_FILE", str(fx.write_pem(tmp_path / "roots.pem", fx.make_ca()[1])))
    chk = probe.check_ws_peer(PEER, 8002, ["synthetic-token"], timeout=2)
    assert chk.status == probe.Status.PASS
    url, kw = captured[0]
    # No per-stack override: the library's default verified context is used,
    # which honours SSL_CERT_FILE.
    assert url.startswith("wss://") and "ssl" not in kw


def test_trust_failure_fails_closed_without_connecting(captured, monkeypatch, tmp_path):
    """A trust failure fails the check closed with no connection and no token."""
    monkeypatch.setenv("PEER_CA_FILE", str(tmp_path / "missing.pem"))
    chk = probe.check_ws_peer(PEER, 8002, ["synthetic-token"], timeout=2)
    assert chk.status == probe.Status.FAIL and "token not sent" in chk.detail
    assert captured == []


def test_websocket_kwargs_selection(monkeypatch, tmp_path):
    """websocket_kwargs returns a context only for wss URLs when trust is configured."""
    monkeypatch.delenv("PEER_PINNED_FINGERPRINTS", raising=False)
    monkeypatch.delenv("PEER_CA_FILE", raising=False)
    peer_tls.clear_cache()
    assert peer_tls.websocket_kwargs(f"ws://{PEER}:8002/ws/portal-peer") == {}
    assert peer_tls.websocket_kwargs(f"wss://{PEER}:8002/ws/portal-peer") == {}
    monkeypatch.setenv("PEER_CA_FILE", str(fx.write_pem(tmp_path / "ca.pem", fx.make_ca()[1])))
    assert peer_tls.websocket_kwargs(f"ws://{PEER}:8002/x") == {}
    assert isinstance(peer_tls.websocket_kwargs(f"wss://{PEER}:8002/x")["ssl"], ssl.SSLContext)


def test_probe_sends_bearer_in_header_only_never_in_url(captured):
    """The probe puts the bearer in the Authorization header and the URL has no query string."""
    chk = probe.check_ws_peer(PEER, 8002, ["synthetic-token"], timeout=2)
    assert chk.status == probe.Status.PASS
    url, kw = captured[0]
    assert "?" not in url and "token" not in url
    assert kw["additional_headers"] == {"Authorization": "Bearer synthetic-token"}
