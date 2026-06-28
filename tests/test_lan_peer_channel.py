"""Tests for lan_peer_channel.py (offline)."""
from __future__ import annotations

import pytest

from orama_system.lan_peer_channel import LanPeerChannel, make_envelope, read_discovery_peer_ip


@pytest.mark.asyncio
async def test_probe_inbound_sends_ack():
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


def test_make_envelope_shape():
    env = make_envelope("heartbeat", {"x": 1})
    assert env["type"] == "heartbeat"
    assert env["source"] in ("mac", "win")
    assert env["data"] == {"x": 1}
    assert isinstance(env["ts"], int)


def test_read_discovery_peer_ip_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "orama_system.lan_peer_channel.Path.home",
        lambda: tmp_path,
    )
    assert read_discovery_peer_ip() == ""
