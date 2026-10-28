"""Live re-resolution of a queued item's peer when its stored address is dead."""
from __future__ import annotations

import argparse
import json
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
LIVE_IP = "203.0.113.20"


@pytest.fixture
def discovery(monkeypatch):
    """Point probe at a Mac-role discovery record whose Windows peer is LIVE_IP; returns the record for edits."""
    record = {"endpoints": {"win": {"ip": LIVE_IP, "port": 1234, "reachable": True}}}
    monkeypatch.setattr(lpa.probe, "load_discovery", lambda: record)
    monkeypatch.setattr(lpa.probe, "local_role", lambda: "mac")
    monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
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


def test_flush_retargets_a_dead_item_and_marks_the_hop_auto(monkeypatch, tmp_path, discovery):
    """The history row records from -> to with auto=True, and the result names the old target."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    task = tmp_path / "task.md"
    task.write_text("# queued for a peer whose address changed\n", encoding="utf-8")
    drop = subprocess.run(
        [
            "python3", str(SCRIPT), "drop", "--peer", "--peer-ip", STALE_IP, "--portal-port", "8002",
            "--file", str(task), "--filename", "win-moved.md", "--assignee", "win", "--topic", "smoke",
        ],
        cwd=ROOT, env={**__import__("os").environ, "HOME": str(home)},
        text=True, capture_output=True, check=False,
    )
    assert json.loads(drop.stdout)["queued"] is True

    _reachable(monkeypatch, (LIVE_IP, 8443))
    seen: dict[str, object] = {}

    def fake_deliver(item, body, meta, ip, port, **kw):
        seen.update(ip=ip, port=port, **kw)
        return {"filename": item["filename"], "status": "delivered", "peer_ip": ip, "portal_port": port}

    monkeypatch.setattr(lpa, "_deliver_item", fake_deliver)
    args = argparse.Namespace(
        only=None, state=None, strict=False, keep_delivered=False, timeout=5, portal_port=8443, peer_ip=None,
    )
    assert lpa.cmd_flush_outbox(args) == 0
    assert (seen["ip"], seen["port"]) == (LIVE_IP, 8443)
    assert seen["auto_retarget"] is True and seen["record_history"] is True


def _queue(monkeypatch, tmp_path, name):
    """Queue one item for STALE_IP:8002 under an isolated HOME and return the filename."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    task = tmp_path / name
    task.write_text("# queued\n", encoding="utf-8")
    subprocess.run(
        [
            "python3", str(SCRIPT), "drop", "--peer", "--peer-ip", STALE_IP, "--portal-port", "8002",
            "--file", str(task), "--filename", name, "--assignee", "win", "--topic", "smoke",
        ],
        cwd=ROOT, env={**__import__("os").environ, "HOME": str(home)},
        text=True, capture_output=True, check=False,
    )
    return name


def _flush_args():
    return argparse.Namespace(
        only=None, state=None, strict=False, keep_delivered=False, timeout=5, portal_port=8443, peer_ip=None,
    )


def _history_row(auto):
    row = {"from": {"peer_ip": STALE_IP, "portal_port": "8002"}, "to": {"peer_ip": LIVE_IP, "portal_port": "8443"}}
    return {**row, "auto": True} if auto else row


@pytest.mark.parametrize("auto, attempted", [(True, True), (False, False)])
def test_only_an_operator_approved_hop_pins_an_item(monkeypatch, tmp_path, discovery, auto, attempted):
    """An auto hop is re-resolved on the next flush; an approved resubmit still needs --only."""
    name = _queue(monkeypatch, tmp_path, "win-pinned.md")
    lpa._set_state(name, "queued", history=[_history_row(auto)])
    _reachable(monkeypatch, (LIVE_IP, 8443))
    calls: list[str] = []

    def fake_deliver(item, body, meta, ip, port, **kw):
        calls.append(item["filename"])
        return {"filename": item["filename"], "status": "delivered", "peer_ip": ip, "portal_port": port}

    monkeypatch.setattr(lpa, "_deliver_item", fake_deliver)
    lpa.cmd_flush_outbox(_flush_args())
    assert (name in calls) is attempted
