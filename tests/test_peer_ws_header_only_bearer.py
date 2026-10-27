"""Peer WebSocket bearer is header-only: client, and the /ws/portal-peer server."""
from __future__ import annotations

import logging
import socket
import sys
import threading
import time
import types
from typing import NoReturn

import pytest
import uvicorn
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import orama_system.portal_server as portal_server
from orama_system.lan_peer_channel import LanPeerChannel, ws_handshake_headers
from utils.endpoint_policy_core import TransportIdentity
from utils.model_endpoint_url import ModelEndpointPolicyError

pytestmark = pytest.mark.unit

GOOD = "synthetic-peer-bearer-0001"
PEER = "192.0.2.10"  # TEST-NET-1


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient for the portal with bearer auth enforced for GOOD and a no-op peer channel."""
    for var in ("ORAMA_CONTROL_PLANE_TOKEN", "ORAMA_CONTROL_PLANE_TOKEN_PEER"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", GOOD)
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")

    async def _noop(*_a: object, **_k: object) -> None:
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
async def test_client_url_has_no_query_and_sends_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """The WS client connects to a query-free URL and passes the bearer as a header."""
    import utils.control_plane_auth as cpa

    monkeypatch.setattr(cpa, "outbound_control_plane_tokens", lambda: ["secret-tok"])
    calls: list[tuple[str, dict]] = []

    class _Conn:
        """Fake connection recording url and kwargs, then ending immediately."""

        def __init__(self, url: str, **kw: object) -> None:
            """Record the connection arguments."""
            calls.append((url, kw))

        async def __aenter__(self) -> _Conn:
            """Return an empty async-iterable socket."""
            return self

        async def __aexit__(self, *exc: object) -> bool:
            """Do not suppress exceptions."""
            return False

        def __aiter__(self) -> _Conn:
            """Return an iterator that yields no frames."""
            return self

        async def __anext__(self) -> NoReturn:
            """End iteration immediately."""
            raise StopAsyncIteration

        async def send(self, _m: object) -> None:
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


def test_server_accepts_valid_header(client: TestClient) -> None:
    """A valid Authorization header is accepted."""
    with client.websocket_connect("/ws/portal-peer", headers=_hdr(GOOD)):
        pass


def test_server_refuses_missing_token(client: TestClient) -> None:
    """TestClient observes the 1008 ASGI close for a pre-upgrade refusal."""
    with pytest.raises(WebSocketDisconnect) as ei, client.websocket_connect("/ws/portal-peer"):
        pass
    assert ei.value.code == 1008


@pytest.mark.integration
def test_network_refusal_is_http_403_before_upgrade(client: TestClient) -> None:
    """A network client receives HTTP 403 when a peer upgrade is refused."""
    host = socket.gethostbyname("localhost")
    server = uvicorn.Server(
        uvicorn.Config(
            portal_server.app,
            host=host,
            port=0,
            ws="websockets",
            log_level="critical",
            access_log=False,
            lifespan="off",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.01)

    try:
        assert server.started
        listener = next(iter(next(iter(server.servers)).sockets or []))
        port = listener.getsockname()[1]
        request = (
            "GET /ws/portal-peer HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Connection: Upgrade\r\n"
            "Upgrade: websocket\r\n"
            "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        with socket.create_connection((host, port), timeout=2) as connection:
            connection.sendall(request.encode("ascii"))
            status_line = connection.recv(1024).splitlines()[0]
        assert status_line == b"HTTP/1.1 403 Forbidden"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
    assert not thread.is_alive()


def test_server_refuses_wrong_token(client: TestClient) -> None:
    """TestClient observes the 1008 ASGI close for a wrong bearer."""
    with pytest.raises(WebSocketDisconnect) as ei, client.websocket_connect("/ws/portal-peer", headers=_hdr("wrong")):
        pass
    assert ei.value.code == 1008


def test_server_refuses_query_token_without_header(client: TestClient) -> None:
    """TestClient observes the 1008 ASGI close for a query credential."""
    with pytest.raises(WebSocketDisconnect) as ei, client.websocket_connect(f"/ws/portal-peer?token={GOOD}"):
        pass
    assert ei.value.code == 1008


def test_server_refuses_any_query_token_even_with_valid_header(client: TestClient) -> None:
    """Any token query parameter is refused even alongside a valid header."""
    with pytest.raises(WebSocketDisconnect) as ei, client.websocket_connect(
        "/ws/portal-peer?token=anything", headers=_hdr(GOOD)
    ):
        pass
    assert ei.value.code == 1008


def test_refusal_never_logs_token_value(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """Refusal logging is a fixed message that never contains the query value."""
    secret = "leaky-query-secret-xyz"
    with caplog.at_level(logging.DEBUG, logger="ultrathink.portal"):
        with pytest.raises(WebSocketDisconnect), client.websocket_connect(
            f"/ws/portal-peer?token={secret}", headers=_hdr(GOOD)
        ):
            pass
    assert "credential query parameters" in caplog.text
    assert secret not in caplog.text and GOOD not in caplog.text


@pytest.mark.asyncio
async def test_client_refuses_bearer_over_plain_ws(monkeypatch: pytest.MonkeyPatch) -> None:
    """With a token and a non-wss URL the client never connects and raises a fixed, secret-free error."""
    import orama_system.lan_peer_channel as lpc
    import utils.control_plane_auth as cpa

    monkeypatch.setattr(cpa, "outbound_control_plane_tokens", lambda: ["secret-tok"])
    monkeypatch.setattr(lpc, "build_peer_transport_url", lambda *a, **k: f"ws://{PEER}:8002/ws/portal-peer")
    calls: list[tuple] = []
    mod = types.ModuleType("websockets")
    mod.connect = lambda *a, **k: calls.append((a, k))
    monkeypatch.setitem(sys.modules, "websockets", mod)
    ident = TransportIdentity(scheme="http", hostname=PEER, port=8002)
    with pytest.raises(ModelEndpointPolicyError) as ei:
        await LanPeerChannel()._ws_client_session(ident, 8002)
    assert calls == []
    assert "secret-tok" not in str(ei.value) and PEER not in str(ei.value)


@pytest.mark.asyncio
async def test_client_sends_header_over_wss(monkeypatch: pytest.MonkeyPatch) -> None:
    """Over wss the bearer header is sent."""
    import orama_system.lan_peer_channel as lpc
    import utils.control_plane_auth as cpa

    monkeypatch.setattr(cpa, "outbound_control_plane_tokens", lambda: ["secret-tok"])
    monkeypatch.setattr(lpc, "build_peer_transport_url", lambda *a, **k: f"wss://{PEER}:9443/ws/portal-peer")
    calls: list[dict] = []

    class _Conn:
        """Fake connection that records kwargs and yields no frames."""

        def __init__(self, url: str, **kw: object) -> None:
            """Record kwargs."""
            calls.append(kw)

        async def __aenter__(self) -> _Conn:
            """Return self."""
            return self

        async def __aexit__(self, *exc: object) -> bool:
            """Do not suppress."""
            return False

        def __aiter__(self) -> _Conn:
            """Return self as iterator."""
            return self

        async def __anext__(self) -> NoReturn:
            """End iteration."""
            raise StopAsyncIteration

    mod = types.ModuleType("websockets")
    mod.connect = _Conn
    monkeypatch.setitem(sys.modules, "websockets", mod)
    await LanPeerChannel()._ws_client_session(TransportIdentity(scheme="https", hostname=PEER, port=9443), 9443)
    assert calls[0]["additional_headers"] == {"Authorization": "Bearer secret-tok"}


@pytest.mark.parametrize("qs", ["TOKEN=x", "access_token=x", "api_key=x"])
def test_server_refuses_credential_query_keys_even_with_valid_header(
    client: TestClient, qs: str
) -> None:
    """Credential-looking query keys are refused case-insensitively, even with a valid header."""
    with pytest.raises(WebSocketDisconnect) as ei, client.websocket_connect(
        f"/ws/portal-peer?{qs}", headers=_hdr(GOOD)
    ):
        pass
    assert ei.value.code == 1008


@pytest.mark.asyncio
async def test_sse_refuses_auth_headers_over_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """An http SSE peer with auth headers makes no HTTP request."""
    import orama_system.lan_peer_channel as lpc
    import utils.control_plane_auth as cpa

    monkeypatch.setattr(cpa, "auth_headers", lambda: {"Authorization": "Bearer secret-tok"})
    monkeypatch.setattr(lpc, "build_peer_transport_url", lambda *a, **k: f"http://{PEER}:8002/events/peer-stream")
    made: list[tuple] = []
    monkeypatch.setattr(lpc.httpx, "AsyncClient", lambda *a, **k: made.append((a, k)))
    with pytest.raises(ModelEndpointPolicyError) as ei:
        await LanPeerChannel()._sse_client_session(TransportIdentity(scheme="http", hostname=PEER, port=8002), 8002)
    assert made == []
    assert "secret-tok" not in str(ei.value) and PEER not in str(ei.value)
