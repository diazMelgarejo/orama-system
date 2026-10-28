"""Opt-in live re-resolution of a queued item's peer when its stored address is dead."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts"
SCRIPT = SCRIPTS / "lan_peer_assign.py"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "src"))

import lan_peer_assign as lpa  # noqa: E402

STALE_IP = "203.0.113.10"
OTHER_NODE_IP = "203.0.113.30"
LIVE_IP = "203.0.113.20"


@pytest.fixture
def discovery(monkeypatch):
    """Point probe at a Mac-role discovery record whose Windows peer is LIVE_IP, with TLS and a pinned CA configured."""
    record = {"endpoints": {"win": {"ip": LIVE_IP, "port": 1234, "reachable": True}}}
    monkeypatch.setattr(lpa.probe, "load_discovery", lambda: record)
    monkeypatch.setattr(lpa.probe, "local_role", lambda: "mac")
    monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
    monkeypatch.setenv("PEER_CA_FILE", "pinned-ca-placeholder.pem")
    monkeypatch.delenv("PEER_PINNED_FINGERPRINTS", raising=False)
    return record


def _reachable(monkeypatch, *open_targets):
    """Make only the listed (ip, port) pairs answer."""
    monkeypatch.setattr(lpa, "_tcp_reachable", lambda ip, port, timeout: (ip.strip("[]"), port) in open_targets)


def test_stored_target_wins_while_it_still_answers(monkeypatch, discovery):
    _reachable(monkeypatch, (STALE_IP, 8002), (LIVE_IP, 8002))
    assert lpa._live_peer_target(STALE_IP, 8002, [8002], timeout=5) is None


def test_dead_stored_target_is_replaced_by_the_live_discovered_host(monkeypatch, discovery):
    _reachable(monkeypatch, (LIVE_IP, 8443))
    assert lpa._live_peer_target(STALE_IP, 8002, [8443], timeout=5) == (LIVE_IP, 8443)


def test_discovered_portal_port_is_tried_before_the_fallbacks(monkeypatch, discovery):
    discovery["endpoints"]["win"]["portal_port"] = 9443
    _reachable(monkeypatch, (LIVE_IP, 9443), (LIVE_IP, 8443))
    assert lpa._live_peer_target(STALE_IP, 8002, [8443], timeout=5) == (LIVE_IP, 9443)


def test_no_retarget_without_peer_tls(monkeypatch, discovery):
    """Bearer tokens must only reach a host that proves itself over pinned https."""
    monkeypatch.delenv("PEER_PORTAL_TLS_ENABLED")
    _reachable(monkeypatch, (LIVE_IP, 8443))
    assert lpa._live_peer_target(STALE_IP, 8002, [8443], timeout=5) is None


def test_no_retarget_without_a_configured_ca_or_pins(monkeypatch, discovery):
    """With neither PEER_CA_FILE nor pins the client falls back to default trust, so 'pinned' would be untrue."""
    monkeypatch.delenv("PEER_CA_FILE")
    _reachable(monkeypatch, (LIVE_IP, 8443))
    assert lpa._live_peer_target(STALE_IP, 8002, [8443], timeout=5) is None
    monkeypatch.setenv("PEER_PINNED_FINGERPRINTS", "ab" * 32)
    assert lpa._live_peer_target(STALE_IP, 8002, [8443], timeout=5) == (LIVE_IP, 8443)


def test_no_retarget_when_discovery_names_the_same_host(monkeypatch, discovery):
    discovery["endpoints"]["win"]["ip"] = STALE_IP
    _reachable(monkeypatch, (STALE_IP, 8443))
    assert lpa._live_peer_target(STALE_IP, 8002, [8443], timeout=5) is None


def test_no_retarget_when_the_live_host_does_not_answer_either(monkeypatch, discovery):
    _reachable(monkeypatch)
    assert lpa._live_peer_target(STALE_IP, 8002, [8443], timeout=5) is None


def test_no_retarget_to_a_malformed_discovered_host(monkeypatch, discovery):
    discovery["endpoints"]["win"]["ip"] = "203.0.113.20:8443"
    _reachable(monkeypatch, ("203.0.113.20:8443", 8443))
    assert lpa._live_peer_target(STALE_IP, 8002, [8443], timeout=5) is None


@pytest.mark.parametrize("bad", [0, 70000, "x", None, True])
def test_out_of_range_discovered_portal_port_is_ignored(bad):
    record = {"endpoints": {"win": {"portal_port": bad}}}
    assert lpa._discovered_portal_ports(record, "win") == []


def test_probe_ceiling_is_capped_so_a_dead_queue_stays_fast(monkeypatch, discovery):
    seen: list[float] = []

    def probe_ip(ip, port, timeout):
        seen.append(timeout)
        return False

    monkeypatch.setattr(lpa, "_tcp_reachable", probe_ip)
    lpa._live_peer_target(STALE_IP, 8002, [8443], timeout=30)
    assert seen and max(seen) <= 1.5


def test_resolution_is_memoised_per_stored_target_within_a_run(monkeypatch, discovery):
    """Many items sharing one dead address cost one resolution, and discovery loads once."""
    loads: list[int] = []
    monkeypatch.setattr(lpa.probe, "load_discovery", lambda: loads.append(1) or discovery)
    calls: list[tuple[str, int]] = []

    def probe_ip(ip, port, timeout):
        calls.append((ip, port))
        return (ip, port) == (LIVE_IP, 8443)

    monkeypatch.setattr(lpa, "_tcp_reachable", probe_ip)
    cache: dict = {}
    first = lpa._live_peer_target(STALE_IP, 8002, [8443], timeout=5, cache=cache)
    probes_after_first = len(calls)
    for _ in range(20):
        assert lpa._live_peer_target(STALE_IP, 8002, [8443], timeout=5, cache=cache) == first
    assert len(calls) == probes_after_first
    lpa._live_peer_target(OTHER_NODE_IP, 8002, [8443], timeout=5, cache=cache)
    assert len(loads) == 1


def _queue(monkeypatch, tmp_path, name, ip=STALE_IP):
    """Queue one item for ip:8002 under an isolated HOME and return the filename."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    task = tmp_path / name
    task.write_text("# queued\n", encoding="utf-8")
    subprocess.run(
        [
            "python3", str(SCRIPT), "drop", "--peer", "--peer-ip", ip, "--portal-port", "8002", "--timeout", "1",
            "--file", str(task), "--filename", name, "--assignee", "win", "--topic", "smoke",
        ],
        cwd=ROOT, env={**os.environ, "HOME": str(home)}, text=True, capture_output=True, check=False,
    )
    return name


def _flush_args(**overrides):
    base = dict(
        only=None, state=None, strict=False, keep_delivered=False, timeout=5, portal_port=8443, peer_ip=None,
        retarget_live=False, retarget_from=[], dry_run=False,
    )
    return argparse.Namespace(**{**base, **overrides})


def _fake_deliver(monkeypatch):
    """Replace delivery with a recorder; returns the list of keyword dicts it was called with."""
    calls: list[dict] = []

    def fake(item, body, meta, ip, port, **kw):
        calls.append({"filename": item["filename"], "ip": ip, "port": port, **kw})
        return {"filename": item["filename"], "status": "delivered", "peer_ip": ip, "portal_port": port}

    monkeypatch.setattr(lpa, "_deliver_item", fake)
    return calls


def test_flush_does_not_retarget_unless_opted_in(monkeypatch, tmp_path, discovery):
    name = _queue(monkeypatch, tmp_path, "win-default.md")
    _reachable(monkeypatch, (LIVE_IP, 8443))
    calls = _fake_deliver(monkeypatch)
    assert lpa.cmd_flush_outbox(_flush_args()) == 0
    assert [(c["filename"], c["ip"], c["port"]) for c in calls] == [(name, STALE_IP, 8002)]
    assert calls[0]["auto_retarget"] is False


def test_flush_retargets_the_named_stale_address_and_marks_the_hop_auto(monkeypatch, tmp_path, discovery):
    name = _queue(monkeypatch, tmp_path, "win-moved.md")
    _reachable(monkeypatch, (LIVE_IP, 8443))
    calls = _fake_deliver(monkeypatch)
    args = _flush_args(retarget_live=True, retarget_from=[STALE_IP])
    assert lpa.cmd_flush_outbox(args) == 0
    assert [(c["filename"], c["ip"], c["port"]) for c in calls] == [(name, LIVE_IP, 8443)]
    assert calls[0]["auto_retarget"] is True and calls[0]["record_history"] is True


def test_an_item_for_another_node_is_never_redirected(monkeypatch, tmp_path, discovery):
    """The misdelivery case: a note queued for a different node whose address is down must stay put."""
    name = _queue(monkeypatch, tmp_path, "win2-note.md", ip=OTHER_NODE_IP)
    _reachable(monkeypatch, (LIVE_IP, 8443))
    calls = _fake_deliver(monkeypatch)
    args = _flush_args(retarget_live=True, retarget_from=[STALE_IP])
    assert lpa.cmd_flush_outbox(args) == 0
    assert [(c["filename"], c["ip"], c["port"]) for c in calls] == [(name, OTHER_NODE_IP, 8002)]
    assert calls[0]["auto_retarget"] is False


def test_dry_run_lists_the_hops_and_sends_nothing(monkeypatch, tmp_path, discovery, capsys):
    name = _queue(monkeypatch, tmp_path, "win-plan.md")
    _reachable(monkeypatch, (LIVE_IP, 8443))
    calls = _fake_deliver(monkeypatch)
    args = _flush_args(retarget_live=True, retarget_from=[STALE_IP], dry_run=True)
    assert lpa.cmd_flush_outbox(args) == 0
    assert calls == []
    out = json.loads(capsys.readouterr().out)
    assert out["dry_run"] is True
    assert out["plan"] == [{"filename": name, "from": f"{STALE_IP}:8002", "to": f"{LIVE_IP}:8443"}]


@pytest.mark.parametrize(
    "overrides, drop_env, message",
    [
        ({"retarget_live": True}, None, "--retarget-from"),
        ({"retarget_live": True, "retarget_from": [STALE_IP]}, "PEER_PORTAL_TLS_ENABLED", "PEER_PORTAL_TLS_ENABLED"),
        ({"retarget_live": True, "retarget_from": [STALE_IP]}, "PEER_CA_FILE", "PEER_CA_FILE"),
        ({"retarget_from": [STALE_IP]}, None, "--retarget-live"),
        ({"dry_run": True}, None, "--retarget-live"),
    ],
)
def test_flush_refuses_unsafe_flag_combinations_loudly(monkeypatch, discovery, overrides, drop_env, message):
    if drop_env:
        monkeypatch.delenv(drop_env)
    with pytest.raises(SystemExit, match=message):
        lpa.cmd_flush_outbox(_flush_args(**overrides))


@pytest.mark.parametrize("auto, attempted", [(True, True), (False, False)])
def test_only_an_operator_approved_hop_pins_an_item(monkeypatch, tmp_path, discovery, auto, attempted):
    """An auto hop is re-resolved on the next flush; an approved resubmit still needs --only."""
    name = _queue(monkeypatch, tmp_path, "win-pinned.md")
    row = {"from": {"peer_ip": STALE_IP, "portal_port": "8002"}, "to": {"peer_ip": LIVE_IP, "portal_port": "8443"}}
    lpa._set_state(name, "queued", history=[{**row, "auto": True} if auto else row])
    _reachable(monkeypatch, (LIVE_IP, 8443))
    calls = _fake_deliver(monkeypatch)
    lpa.cmd_flush_outbox(_flush_args())
    assert (name in [c["filename"] for c in calls]) is attempted
