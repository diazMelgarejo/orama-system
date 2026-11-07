"""flush-outbox --remap-port: queued http-port items reach the peer's https port, and nothing else moves."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_lan_peer_live_resolve import (  # noqa: E402,F401  (also puts the harness scripts on sys.path)
    LIVE_IP,
    OTHER_NODE_IP,
    STALE_IP,
    _fake_deliver,
    _flush_args,
    _queue,
    discovery,
)

import lan_peer_assign as lpa  # noqa: E402

PEER = STALE_IP


def _targets(calls: list[dict]) -> list[tuple[str, str, int]]:
    """Reduce recorded delivery calls to (filename, ip, port) tuples."""
    return [(c["filename"], c["ip"], c["port"]) for c in calls]


def test_without_the_flag_a_queued_item_keeps_its_stored_http_port(monkeypatch, tmp_path, discovery):
    """The default is unchanged: the stored target wins."""
    name = _queue(monkeypatch, tmp_path, "peer-a.md", ip=PEER)
    calls = _fake_deliver(monkeypatch)
    assert lpa.cmd_flush_outbox(_flush_args()) == 0
    assert _targets(calls) == [(name, PEER, 8002)]


def test_remap_sends_the_named_peers_item_to_the_https_port_and_records_the_hop(monkeypatch, tmp_path, discovery):
    """An item stored on the plain port for the named peer is delivered on the https port with a history trail."""
    name = _queue(monkeypatch, tmp_path, "peer-b.md", ip=PEER)
    calls = _fake_deliver(monkeypatch)
    args = _flush_args(remap_port=["8002:8443"], remap_peer_ip=[PEER])
    assert lpa.cmd_flush_outbox(args) == 0
    assert _targets(calls) == [(name, PEER, 8443)]
    assert calls[0]["record_history"] is True and calls[0]["auto_retarget"] is True


def test_remap_never_moves_an_item_stored_for_another_peer(monkeypatch, tmp_path, discovery):
    """An item for a different node stays on its own address and port."""
    name = _queue(monkeypatch, tmp_path, "other-node.md", ip=OTHER_NODE_IP)
    calls = _fake_deliver(monkeypatch)
    args = _flush_args(remap_port=["8002:8443"], remap_peer_ip=[PEER])
    assert lpa.cmd_flush_outbox(args) == 0
    assert _targets(calls) == [(name, OTHER_NODE_IP, 8002)]
    assert calls[0]["auto_retarget"] is False


def test_remap_ignores_items_stored_on_other_ports(monkeypatch, tmp_path, discovery):
    """Only the FROM port is remapped."""
    name = _queue(monkeypatch, tmp_path, "peer-c.md", ip=PEER)
    calls = _fake_deliver(monkeypatch)
    args = _flush_args(remap_port=["9000:8443"], remap_peer_ip=[PEER])
    assert lpa.cmd_flush_outbox(args) == 0
    assert _targets(calls) == [(name, PEER, 8002)]


def test_an_operator_approved_destination_is_not_remapped(monkeypatch, tmp_path, discovery):
    """A resubmitted item resent with --only goes to the destination the operator approved, never the remap."""
    name = _queue(monkeypatch, tmp_path, "peer-d.md", ip=PEER)
    hop = {
        "from": {"peer_ip": PEER, "portal_port": "8002"},
        "to": {"peer_ip": LIVE_IP, "portal_port": "8002"},
    }
    lpa._set_state(name, "queued", history=[hop])
    calls = _fake_deliver(monkeypatch)
    args = _flush_args(only=[name], remap_port=["8002:8443"], remap_peer_ip=[LIVE_IP])
    lpa.cmd_flush_outbox(args)
    assert _targets(calls) == [(name, LIVE_IP, 8002)]


@pytest.mark.parametrize(
    "overrides, drop_env, message",
    [
        ({"remap_port": ["8002:8443"]}, None, "--remap-peer-ip"),
        ({"remap_peer_ip": [PEER]}, None, "--remap-port"),
        ({"remap_port": ["8002:8443"], "remap_peer_ip": [PEER]}, "PEER_PORTAL_TLS_ENABLED", "PEER_PORTAL_TLS_ENABLED"),
        ({"remap_port": ["8002:8443"], "remap_peer_ip": [PEER]}, "PEER_CA_FILE", "PEER_CA_FILE"),
        ({"remap_port": ["8002"], "remap_peer_ip": [PEER]}, None, "FROM:TO"),
        ({"remap_port": ["8002:x"], "remap_peer_ip": [PEER]}, None, "FROM:TO"),
        ({"remap_port": ["8002:70000"], "remap_peer_ip": [PEER]}, None, "1-65535"),
        ({"remap_port": ["0:8443"], "remap_peer_ip": [PEER]}, None, "1-65535"),
    ],
)
def test_remap_refuses_unsafe_or_malformed_options(monkeypatch, discovery, overrides, drop_env, message):
    """Remapping needs a named peer, https with a pinned CA, and well-formed ports."""
    if drop_env:
        monkeypatch.delenv(drop_env)
    with pytest.raises(SystemExit, match=message):
        lpa.cmd_flush_outbox(_flush_args(**overrides))
