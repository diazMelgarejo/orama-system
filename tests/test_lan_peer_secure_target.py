"""With peer TLS on, the portal dials the peer's https front end and trusts only the operator's certificates."""
from __future__ import annotations

import json
import ssl
from pathlib import Path

import pytest

import peer_tls_fixtures as fx
from utils.endpoint_policy_core import TransportIdentity
from utils.model_endpoint_url import ModelEndpointPolicyError

pytestmark = pytest.mark.unit

TOKEN = fx.SYNTHETIC_TOKEN
PLAIN_PORT = 8002
PEER = TransportIdentity(scheme="http", hostname="localhost")
BEARER = f"Bearer {TOKEN}"
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _isolated_peer_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No developer settings or discovery file may reach these tests."""
    for name in ("PEER_PORTAL_TLS_ENABLED", "PEER_PORTAL_TLS_PORT", "PEER_CA_FILE", "PEER_CA_SHA256",
                 "PEER_PINNED_FINGERPRINTS", "ORAMA_PLATFORM"):
        monkeypatch.delenv(name, raising=False)
    for name in ("https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ORAMA_PLATFORM", "mac")
    monkeypatch.setattr("orama_system.lan_peer_channel.Path.home", lambda: tmp_path)


def _discovery(tmp_path: Path, **win: object) -> None:
    state = tmp_path / ".openclaw" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "last_discovery.json").write_text(
        json.dumps({"endpoints": {"win": {"ip": "localhost", **win}}}), encoding="utf-8")


def _trusted_server(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> fx.PeerServer:
    """An https peer signed by a throwaway CA that this stack is configured to trust."""
    ca_key, ca = fx.make_ca()
    leaf = fx.make_leaf(issuer=(ca_key, ca))
    monkeypatch.setenv("PEER_CA_FILE", str(fx.write_pem(tmp_path / "ca.pem", ca)))
    server = fx.start_server(tmp_path, leaf)
    monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
    monkeypatch.setenv("PEER_PORTAL_TLS_PORT", str(server.port))
    return server


def _distrust(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point the stack at a different CA than the one that signed the server."""
    _, other = fx.make_ca("another-ca")
    monkeypatch.setenv("PEER_CA_FILE", str(fx.write_pem(tmp_path / "other-ca.pem", other)))


# ------------------------------------------------------------------ choosing the target


def test_plain_target_is_unchanged_while_peer_tls_is_off(tmp_path: Path) -> None:
    from orama_system.lan_peer_channel import peer_portal_target

    _discovery(tmp_path, portal_port=9443)

    assert peer_portal_target(PEER, PLAIN_PORT) == (PEER, PLAIN_PORT)


@pytest.mark.parametrize(
    "setting, saved, expected",
    [
        (None, 9443, 9443),          # the saved secure port
        ("9555", 9443, 9555),        # an explicit setting wins
        (None, PLAIN_PORT, 8443),    # a saved plain port cannot serve https
        (None, None, 8443),
        (None, True, 8443),
        (None, "junk", 8443),
        (None, 70000, 8443),
    ],
)
def test_peer_tls_selects_https_and_the_secure_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, setting: str | None, saved: object, expected: int
) -> None:
    from orama_system.lan_peer_channel import peer_portal_target

    monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
    if setting:
        monkeypatch.setenv("PEER_PORTAL_TLS_PORT", setting)
    if saved is not None:
        _discovery(tmp_path, portal_port=saved)

    identity, port = peer_portal_target(PEER, PLAIN_PORT)

    assert (identity.scheme, identity.hostname, port) == ("https", "localhost", expected)


@pytest.mark.parametrize("setting", ["abc", "0", "70000", "-1"])
def test_an_invalid_secure_port_setting_is_refused(monkeypatch: pytest.MonkeyPatch, setting: str) -> None:
    from orama_system.lan_peer_channel import peer_portal_target

    monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
    monkeypatch.setenv("PEER_PORTAL_TLS_PORT", setting)

    with pytest.raises(ModelEndpointPolicyError):
        peer_portal_target(PEER, PLAIN_PORT)


# ------------------------------------------------------------------ the background WebSocket and stream


async def _websocket_session(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, trust: bool) -> list[str]:
    """Run the channel's real client against a real wss server; return the Authorization headers it received."""
    import websockets

    import orama_system.lan_peer_channel as lpc
    import utils.control_plane_auth as cpa

    ca_key, ca = fx.make_ca()
    key, cert = fx.make_leaf(issuer=(ca_key, ca))
    server_tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_tls.load_cert_chain(str(fx.write_pem(tmp_path / "leaf.pem", cert, key)))
    monkeypatch.setenv("PEER_CA_FILE", str(fx.write_pem(tmp_path / "ca.pem", ca)))
    if not trust:
        _distrust(monkeypatch, tmp_path)
    monkeypatch.setattr(cpa, "outbound_control_plane_tokens", lambda: [TOKEN])
    seen: list[str] = []

    async def handler(ws) -> None:
        seen.append(ws.request.headers.get("Authorization", ""))
        await ws.close()

    async with websockets.serve(handler, fx.LOOPBACK_V4, 0, ssl=server_tls) as server:
        port = next(iter(server.sockets)).getsockname()[1]
        monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
        monkeypatch.setenv("PEER_PORTAL_TLS_PORT", str(port))
        await lpc.LanPeerChannel()._ws_client_session(PEER, PLAIN_PORT)
    return seen


async def test_background_websocket_connects_over_verified_tls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert await _websocket_session(monkeypatch, tmp_path, trust=True) == [BEARER]


async def test_background_websocket_sends_nothing_to_an_untrusted_certificate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(ssl.SSLCertVerificationError):
        await _websocket_session(monkeypatch, tmp_path, trust=False)


async def test_stream_fallback_connects_over_verified_tls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import orama_system.lan_peer_channel as lpc
    import utils.control_plane_auth as cpa

    monkeypatch.setattr(cpa, "auth_headers", lambda: {"Authorization": BEARER})
    server = _trusted_server(monkeypatch, tmp_path)
    try:
        await lpc.LanPeerChannel()._sse_client_session(PEER, PLAIN_PORT)
    finally:
        server.stop()

    assert server.seen == [("GET", "/events/peer-stream", BEARER)]


# ------------------------------------------------------------------ the portal's inbox mirror


def _portal(monkeypatch: pytest.MonkeyPatch):
    from orama_system import portal_server

    monkeypatch.setattr(portal_server, "read_discovery_peer_identity", lambda: PEER)
    monkeypatch.setattr(portal_server, "auth_headers", lambda: {"Authorization": BEARER})
    return portal_server


async def test_portal_inbox_list_uses_verified_tls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    portal_server = _portal(monkeypatch)
    server = _trusted_server(monkeypatch, tmp_path)
    server.reply = {"files": [{"filename": "note.md"}]}
    try:
        files, error = await portal_server._fetch_peer_inbox_remote()
    finally:
        server.stop()

    assert (files, error) == ([{"filename": "note.md"}], "")
    assert server.seen == [("GET", "/api/peer-inbox", BEARER)]


async def test_portal_inbox_mirror_uses_verified_tls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    portal_server = _portal(monkeypatch)
    server = _trusted_server(monkeypatch, tmp_path)
    server.reply = {"files": []}
    try:
        result = await portal_server._fetch_remote_peer_api("/api/peer-inbox")
    finally:
        server.stop()

    assert result["ok"] is True, result
    assert server.seen == [("GET", "/api/peer-inbox", BEARER)]


async def test_portal_inbox_mirror_sends_nothing_to_an_untrusted_certificate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    portal_server = _portal(monkeypatch)
    server = _trusted_server(monkeypatch, tmp_path)
    _distrust(monkeypatch, tmp_path)
    try:
        result = await portal_server._fetch_remote_peer_api("/api/peer-inbox")
    finally:
        server.stop()

    assert result["ok"] is False and "CERTIFICATE_VERIFY_FAILED" in result["error"], result
    assert server.seen == []


async def test_portal_inbox_mirror_reports_an_unusable_ca_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    portal_server = _portal(monkeypatch)
    monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
    monkeypatch.setenv("PEER_CA_FILE", str(tmp_path / "absent.pem"))

    result = await portal_server._fetch_remote_peer_api("/api/peer-inbox")

    assert result["ok"] is False and "PEER_CA_FILE" in result["error"]


def test_every_portal_peer_url_goes_through_the_secure_target() -> None:
    """A portal caller that builds a peer URL directly would silently fall back to the plain port."""
    source = (ROOT / "src/orama_system/portal_server.py").read_text(encoding="utf-8")

    assert "build_peer_transport_url(" not in source
