"""Peer WebSocket bearer is header-only: client, and the /ws/portal-peer server."""
from __future__ import annotations

import logging
import sys
import types

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import orama_system.portal_server as portal_server
from orama_system.lan_peer_channel import LanPeerChannel, ws_handshake_headers
from utils.endpoint_policy_core import TransportIdentity

pytestmark = pytest.mark.unit

GOOD = "synthetic-peer-bearer-0001"
PEER = "192.0.2.10"  # TEST-NET-1


@pytest.fixture
def client(monkeypatch):
    """TestClient for the portal with bearer auth enforced for GOOD and a no-op peer channel."""
    for var in ("ORAMA_CONTROL_PLANE_TOKEN", "ORAMA_CONTROL_PLANE_TOKEN_PEER"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", GOOD)
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")

    async def _noop(*_a, **_k):
        """Do nothing."""
        return None

    monkeypatch.setattr(portal_server._lan_peer_channel, "register_ws_peer", _noop)
    monkeypatch.setattr(portal_server._lan_peer_channel, "unregister_ws_peer", _noop)
    return TestClient(portal_server.app)


def _hdr(token: str) -> dict[str, str]:
    """Return an Authorization header for token."""
    return {"Authorization": f"Bearer {token}"}


def test_ws_headers_helper() -> None:
    """The helper yields a bearer header for a token and nothing without one."""
    assert ws_handshake_headers("abc") == {"Authorization": "Bearer abc"}
    assert ws_handshake_headers("") is None


@pytest.mark.asyncio
async def test_client_url_has_no_query_and_sends_header(monkeypatch) -> None:
    """The WS client connects to a query-free URL and passes the bearer as a header."""
    import utils.control_plane_auth as cpa

    monkeypatch.setattr(cpa, "outbound_control_plane_tokens", lambda: ["secret-tok"])
    calls: list[tuple[str, dict]] = []

    class _Conn:
        """Fake connection recording url and kwargs, then ending immediately."""

        def __init__(self, url, **kw):
            """Record the connection arguments."""
            calls.append((url, kw))

        async def __aenter__(self):
            """Return an empty async-iterable socket."""
            return self

        async def __aexit__(self, *exc):
            """Do not suppress exceptions."""
            return False

        def __aiter__(self):
            """Return an iterator that yields no frames."""
            return self

        async def __anext__(self):
            """End iteration immediately."""
            raise StopAsyncIteration

        async def send(self, _m):
            """Ignore sends."""

    mod = types.ModuleType("websockets")
    mod.connect = _Conn
    monkeypatch.setitem(sys.modules, "websockets", mod)
    ch = LanPeerChannel()
    ident = TransportIdentity(scheme="https", hostname=PEER, port=9443)
    await ch._ws_client_session(ident, 9443)
    url, kw = calls[0]
    assert "?" not in url and "secret-tok" not in url
    assert kw["additional_headers"] == {"Authorization": "Bearer secret-tok"}


def test_server_accepts_valid_header(client) -> None:
    """A valid Authorization header is accepted."""
    with client.websocket_connect("/ws/portal-peer", headers=_hdr(GOOD)):
        pass


def test_server_refuses_missing_token(client) -> None:
    """No credential is refused with 1008 before accept."""
    with pytest.raises(WebSocketDisconnect) as ei, client.websocket_connect("/ws/portal-peer"):
        pass
    assert ei.value.code == 1008


def test_server_refuses_wrong_token(client) -> None:
    """A wrong bearer is refused."""
    with pytest.raises(WebSocketDisconnect) as ei, client.websocket_connect("/ws/portal-peer", headers=_hdr("wrong")):
        pass
    assert ei.value.code == 1008


def test_server_refuses_query_token_without_header(client) -> None:
    """A valid token in the query string is refused."""
    with pytest.raises(WebSocketDisconnect) as ei, client.websocket_connect(f"/ws/portal-peer?token={GOOD}"):
        pass
    assert ei.value.code == 1008


def test_server_refuses_any_query_token_even_with_valid_header(client) -> None:
    """Any token query parameter is refused even alongside a valid header."""
    with pytest.raises(WebSocketDisconnect) as ei, client.websocket_connect(
        "/ws/portal-peer?token=anything", headers=_hdr(GOOD)
    ):
        pass
    assert ei.value.code == 1008


def test_refusal_never_logs_token_value(client, caplog) -> None:
    """Refusal logging is a fixed message that never contains the query value."""
    secret = "leaky-query-secret-xyz"
    with caplog.at_level(logging.DEBUG, logger="ultrathink.portal"):
        with pytest.raises(WebSocketDisconnect), client.websocket_connect(
            f"/ws/portal-peer?token={secret}", headers=_hdr(GOOD)
        ):
            pass
    assert "token query parameter" in caplog.text
    assert secret not in caplog.text and GOOD not in caplog.text
