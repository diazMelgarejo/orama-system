"""Tests for lan_peer_channel.py (offline)."""
from __future__ import annotations

import json

import pytest

from orama_system.lan_peer_channel import (
    LanPeerChannel,
    build_peer_transport_url,
    make_envelope,
    read_discovery_peer_identity,
    read_discovery_peer_ip,
)
from utils.endpoint_policy_core import TransportIdentity
from utils.model_endpoint_url import ModelEndpointPolicyError

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_probe_inbound_sends_ack() -> None:
    channel = LanPeerChannel()
    sent: list[dict] = []

    async def capture(event: dict) -> None:
        sent.append(event)

    channel.register_inbound_handler(capture)
    await channel.on_inbound({"type": "probe", "source": "mac"})
    assert sent == []
    assert channel._out_queue.qsize() == 1
    event = channel._out_queue.get_nowait()
    assert event["type"] == "probe-ack"
    assert event["data"]["ok"] is True


def test_make_envelope_shape() -> None:
    env = make_envelope("heartbeat", {"x": 1})
    assert env["type"] == "heartbeat"
    assert env["source"] in ("mac", "win")
    assert env["data"] == {"x": 1}
    assert isinstance(env["ts"], int)


def test_read_discovery_peer_ip_missing_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "orama_system.lan_peer_channel.Path.home",
        lambda: tmp_path,
    )
    assert read_discovery_peer_ip() == ""


def _write_discovery_file(tmp_path, role_key: str, ip_value: str) -> None:
    state_dir = tmp_path / ".openclaw" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "last_discovery.json").write_text(
        json.dumps({"endpoints": {role_key: {"ip": ip_value}}}),
        encoding="utf-8",
    )


def test_read_discovery_peer_ip_normalizes_scheme_contaminated_value(monkeypatch, tmp_path) -> None:
    """Regression: the "ip" field is written by a separate process
    (scripts/discover.py); the read side previously trusted it verbatim.
    If that field is ever accidentally scheme-prefixed (e.g.
    "http://192.168.1.5" instead of a bare IP), every downstream caller
    that does f"http://{peer_ip}:{port}" would construct a double-scheme
    URL. read_discovery_peer_ip must normalize to a bare hostname."""
    monkeypatch.setattr("orama_system.lan_peer_channel.Path.home", lambda: tmp_path)
    monkeypatch.setattr("orama_system.lan_peer_channel.local_platform", lambda: "win")
    _write_discovery_file(tmp_path, "mac", "http://192.168.1.5")

    result = read_discovery_peer_ip()

    assert result == "192.168.1.5"
    assert "http://" not in result


def test_read_discovery_peer_ip_rejects_malformed_value(monkeypatch, tmp_path) -> None:
    """A value parse_transport_identity cannot make sense of (credentials
    embedded, unparseable) must be rejected outright, not passed through."""
    monkeypatch.setattr("orama_system.lan_peer_channel.Path.home", lambda: tmp_path)
    monkeypatch.setattr("orama_system.lan_peer_channel.local_platform", lambda: "win")
    _write_discovery_file(tmp_path, "mac", "http://user:pass@192.168.1.5")

    assert read_discovery_peer_ip() == ""


def test_read_discovery_peer_ip_passes_through_bare_ip_unchanged(monkeypatch, tmp_path) -> None:
    """The common, expected case -- a plain IP -- must still work exactly
    as before; the fix must not be over-broad."""
    monkeypatch.setattr("orama_system.lan_peer_channel.Path.home", lambda: tmp_path)
    monkeypatch.setattr("orama_system.lan_peer_channel.local_platform", lambda: "win")
    _write_discovery_file(tmp_path, "mac", "192.168.254.107")

    assert read_discovery_peer_ip() == "192.168.254.107"


def test_read_discovery_peer_identity_preserves_https(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("orama_system.lan_peer_channel.Path.home", lambda: tmp_path)
    monkeypatch.setattr("orama_system.lan_peer_channel.local_platform", lambda: "win")
    _write_discovery_file(tmp_path, "mac", "https://192.168.254.107:9443")

    assert read_discovery_peer_identity() == TransportIdentity(
        scheme="https",
        hostname="192.168.254.107",
        port=9443,
    )


def test_build_peer_transport_url_preserves_secure_transport() -> None:
    identity = TransportIdentity(scheme="https", hostname="192.168.254.107", port=9443)

    assert build_peer_transport_url(identity, 8002, "/ws/portal-peer", websocket=True) == (
        "wss://192.168.254.107:8002/ws/portal-peer"
    )
    assert build_peer_transport_url(identity, 8002, "/events/peer-stream", websocket=False) == (
        "https://192.168.254.107:8002/events/peer-stream"
    )


def test_build_peer_transport_url_rejects_public_target() -> None:
    identity = TransportIdentity(scheme="https", hostname="1.1.1.1", port=9443)

    with pytest.raises(ModelEndpointPolicyError):
        build_peer_transport_url(identity, 8002, "/ws/portal-peer", websocket=True)
