"""Regression tests for 3 bugs found 2026-07-19 running the fleet-mesh
mother plan against REAL peer data for the first time.

All 125 pre-existing fleet tests passed throughout -- because
tests/fixtures/fleet_topology_fixtures.py's mock peer responses use
`peers: [{"id": ..., "ip": ..., ...}]` (the mother plan's original
design-doc example schema), which is NOT what the canonical writer
(PT orchestrator/fleet_topology.py's FleetTopologyState, which
query_peer_topology.py writes against) actually produces:
`peers: list[str]` -- bare node-id strings (see FleetTopologyState's own
docstring: "list of reachable peer identifiers"). Synthetic fixtures and
the real writer had silently diverged; nothing caught it because nothing
tested the real shape. This is the second time this exact class of gap
(synthetic-passes / real-data-fails) showed up in the same session -- see
PT lesson_7155c5157bd4 ("verify against real production data, not just
synthetic tests").

Bugs covered:
  1. query_peer_topology._merge_peer_topology()'s "no current state" seed
     branch used the PEER's self-reported local_node as THIS node's own
     identity, making peers_reachable miscount to 0 (SOLO) even with a
     live, successfully-merged peer.
  2. display_fleet_status.load_fleet_topology() crashed with
     AttributeError on the real flat-string peers schema.
  3. display_fleet_status's peers_reachable double-counted the local node
     as its own peer once (2) was naively fixed to accept strings.
"""
from __future__ import annotations

import importlib.util
import json
import socket
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from orama_system.display_fleet_status import (  # noqa: E402
    load_fleet_topology,
    FleetPeer,
)

_QPT_PATH = (
    _REPO_ROOT / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts"
    / "query_peer_topology.py"
)
_spec = importlib.util.spec_from_file_location("query_peer_topology", _QPT_PATH)
qpt = importlib.util.module_from_spec(_spec)
sys.modules["query_peer_topology"] = qpt
_spec.loader.exec_module(qpt)  # type: ignore[union-attr]


def _orchestrator_available() -> bool:
    """True when Perpetua-Tools is co-located (local dev), not in orama-only CI."""
    try:
        qpt._ensure_pt_on_path()
        qpt._import_orchestrator()
        return True
    except ImportError:
        return False


_requires_orchestrator = pytest.mark.skipif(
    not _orchestrator_available(),
    reason=(
        "requires Perpetua-Tools checked out as a sibling of orama-system "
        "(not present in orama-system CI)"
    ),
)


# ── D9: _http_get retries across token candidates on 401 ────────────────
# Covered end-to-end for probe_lan_peer.py's relay_probe() in
# test_probe_lan_peer_relay.py, but query_peer_topology.py's own _http_get()
# (the actual D9 fix site -- see its docstring) never had a dedicated unit
# test locking in the retry-on-401 behavior.


@pytest.mark.unit
def test_http_get_retries_next_token_on_401(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_urlopen(req: urllib.request.Request, timeout: float = 2):
        token = req.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        calls.append(token)
        if token == "bad":
            raise qpt.urllib.error.HTTPError(
                req.full_url, 401, "Unauthorized", hdrs=None, fp=None
            )
        body = json.dumps({"ok": True}).encode("utf-8")

        class _Resp:
            def read(self) -> bytes:
                return body

            def __enter__(self):
                return self

            def __exit__(self, *args: Any) -> bool:
                return False

        return _Resp()

    monkeypatch.setattr(qpt.probe, "outbound_control_plane_tokens", lambda: ["bad", "good"])
    monkeypatch.setattr(qpt.urllib.request, "urlopen", fake_urlopen)

    # https:// -- a real token candidate is only ever attempted over
    # authenticated transport (see _is_authenticated_transport); this test
    # exercises the retry-across-candidates logic specifically, which is
    # still valid and still runs once that precondition is satisfied.
    result = qpt._http_get("https://10.0.0.50:8002/api/fleet-topology")

    assert result == {"ok": True}
    assert calls == ["bad", "good"]  # tried the rejected candidate first, then the working one
    assert len(calls) == 2  # ALL candidates were attempted, not short-circuited


@pytest.mark.unit
def test_http_get_returns_none_when_all_candidates_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_urlopen(req: urllib.request.Request, timeout: float = 2):
        token = req.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        calls.append(token)
        raise qpt.urllib.error.HTTPError(req.full_url, 401, "Unauthorized", hdrs=None, fp=None)

    monkeypatch.setattr(qpt.probe, "outbound_control_plane_tokens", lambda: ["bad1", "bad2"])
    monkeypatch.setattr(qpt.urllib.request, "urlopen", fake_urlopen)

    assert qpt._http_get("https://10.0.0.50:8002/api/fleet-topology") is None
    assert len(calls) == 2  # both candidates exhausted before giving up


@pytest.mark.unit
def test_http_get_refuses_bearer_token_over_unauthenticated_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression for the security-review fix: a real control-plane token
    candidate must never be attempted over plain http:// -- not even the
    first one. The whole retry loop must never call urlopen() at all."""
    called = {"n": 0}

    def fake_urlopen(req: urllib.request.Request, timeout: float = 2):
        called["n"] += 1
        raise AssertionError("urlopen must never be called over unauthenticated transport")

    monkeypatch.setattr(qpt.probe, "outbound_control_plane_tokens", lambda: ["real-token"])
    monkeypatch.setattr(qpt.urllib.request, "urlopen", fake_urlopen)

    result = qpt._http_get("http://10.0.0.50:8002/api/fleet-topology")

    assert result is None
    assert called["n"] == 0


@pytest.mark.unit
def test_http_get_allows_no_token_over_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """A request with NO token candidates (nothing to leak) may still
    proceed over http:// -- the security gate only blocks real credentials,
    not unauthenticated no-token requests."""
    body = json.dumps({"ok": True}).encode("utf-8")

    class _Resp:
        def read(self) -> bytes:
            return body

        def __enter__(self):
            return self

        def __exit__(self, *args: Any) -> bool:
            return False

    def _fake_urlopen_no_token(req: urllib.request.Request, timeout: float = 2):
        return _Resp()

    monkeypatch.setattr(qpt.probe, "outbound_control_plane_tokens", lambda: [])
    monkeypatch.setattr(qpt.urllib.request, "urlopen", _fake_urlopen_no_token)

    result = qpt._http_get("http://10.0.0.50:8002/api/fleet-topology")

    assert result == {"ok": True}


# ── Bug 1: seed-branch local_node identity ──────────────────────────────


@_requires_orchestrator
def test_merge_seed_uses_own_hostname_not_peers_self_report():
    """First-ever merge (current=None) must seed local_node from THIS
    machine, never from the peer's payload -- and must count the peer as
    reachable, not zero."""
    peer_data = {
        "local_node": "win-studio",  # the PEER's own name -- must NOT leak into ours
        "fleet_mode": "SOLO",
        "peers": [],
        "cross_reachable": False,
        "queried_at": time.time(),
    }
    state, _events = qpt._merge_peer_topology(None, peer_data, "10.0.0.2")
    assert state is not None
    assert state.local_node == socket.gethostname()
    assert state.local_node != "win-studio"
    assert "win-studio" in state.peers
    assert state.local_node in state.peers
    peers_reachable = (
        len(state.peers) - 1 if state.local_node in state.peers else len(state.peers)
    )
    assert peers_reachable == 1  # NOT 0 -- this is the exact SOLO-misclassification bug


@_requires_orchestrator
def test_merge_seed_classifies_pair_not_solo():
    """End-to-end: a single successful peer merge from a clean slate must
    classify PAIR, matching the mother plan's own SOLO/PAIR/FLEET
    definitions -- 1 peer reachable is PAIR, not SOLO."""
    peer_data = {
        "local_node": "win-studio",
        "fleet_mode": "SOLO",
        "peers": [],
        "cross_reachable": False,
        "queried_at": time.time(),
    }
    state, _ = qpt._merge_peer_topology(None, peer_data, "10.0.0.2")
    from orchestrator.startup_intelligence import FleetMode  # noqa: E402
    assert state.fleet_mode == FleetMode.PAIR


@_requires_orchestrator
def test_merge_second_call_preserves_seeded_local_node():
    """A subsequent merge (current already set) must keep reusing the
    correctly-seeded local_node, not re-derive or drift it."""
    peer_data = {"local_node": "win-studio", "fleet_mode": "SOLO", "peers": [],
                  "cross_reachable": False, "queried_at": time.time()}
    first, _ = qpt._merge_peer_topology(None, peer_data, "10.0.0.2")
    second_peer_data = {"local_node": "win-studio", "fleet_mode": "PAIR",
                         "peers": ["win-rtx5080"], "cross_reachable": True,
                         "queried_at": time.time()}
    second, _ = qpt._merge_peer_topology(first, second_peer_data, "10.0.0.2")
    assert second.local_node == first.local_node == socket.gethostname()
    assert "win-rtx5080" in second.peers


# ── Bug 2 + 3: display_fleet_status real-schema parsing ─────────────────


def _write_topology(tmp_path: Path, **overrides) -> Path:
    data = {
        "local_node": "Mac-Studio.local",
        "fleet_mode": "PAIR",
        "peers": ["Mac-Studio.local", "win-studio"],  # REAL shape: flat strings
        "cross_reachable": False,
        "timestamp": time.time(),
    }
    data.update(overrides)
    path = tmp_path / "fleet_topology.json"
    path.write_text(json.dumps(data))
    return path


def test_load_fleet_topology_accepts_real_flat_string_peers(tmp_path):
    """Must not raise on the canonical writer's actual list[str] shape."""
    path = _write_topology(tmp_path)
    status = load_fleet_topology(path)
    assert status is not None
    assert status.fleet_mode == "PAIR"


def test_load_fleet_topology_excludes_local_node_from_peer_list(tmp_path):
    """The local node's own id (present in the raw peers list per the
    writer's own schema) must not appear in FleetStatus.peers, and must
    not be double-counted in peers_reachable."""
    path = _write_topology(tmp_path)
    status = load_fleet_topology(path)
    peer_ids = [p.id for p in status.peers]
    assert "Mac-Studio.local" not in peer_ids
    assert "win-studio" in peer_ids
    assert status.peers_reachable == 1  # NOT 2 -- the exact double-count bug


def test_load_fleet_topology_still_accepts_dict_shaped_peers(tmp_path):
    """Backward compat: the mother plan's original richer per-peer dict
    schema (id/ip/port/reachable/models/last_seen) must still work,
    matching tests/fixtures/fleet_topology_fixtures.py's existing mocks."""
    path = _write_topology(
        tmp_path,
        peers=[
            {"id": "Mac-Studio.local", "ip": "127.0.0.1", "reachable": True},
            {"id": "win-rtx5080", "ip": "192.168.1.102", "port": 8002,
             "reachable": True, "models": ["gemma-4-26b"], "last_seen": "now"},
        ],
    )
    status = load_fleet_topology(path)
    peer_ids = [p.id for p in status.peers]
    assert peer_ids == ["win-rtx5080"]
    assert status.peers[0].ip == "192.168.1.102"
    assert status.peers[0].models == ["gemma-4-26b"]


def test_load_fleet_topology_mixed_shapes_do_not_crash(tmp_path):
    """A raw peers list mixing bare strings and dicts (shouldn't happen in
    practice, but must fail safe, never raise) is handled entry-by-entry."""
    path = _write_topology(tmp_path, peers=["Mac-Studio.local", {"id": "win-rtx5080", "ip": "1.2.3.4"}])
    status = load_fleet_topology(path)
    assert status is not None
    assert [p.id for p in status.peers] == ["win-rtx5080"]
