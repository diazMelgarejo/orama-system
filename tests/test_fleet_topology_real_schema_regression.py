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
from pathlib import Path
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


def _load_query_peer_topology():
    """Load query_peer_topology.py only when Perpetua-Tools is co-located.

    orama-system CI checks out this repo alone (no PT sibling), so merge tests
    that exercise PT's FleetTopologyState must skip gracefully there — same
    pattern as tests/test_topology_watch.py.
    """
    pytest.importorskip(
        "orchestrator.fleet_topology",
        reason="requires Perpetua-Tools checked out as a sibling of orama-system",
    )
    for candidate in (
        _REPO_ROOT.parent / "perplexity-api" / "Perpetua-Tools",
        _REPO_ROOT.parent / "Perpetua-Tools",
        _REPO_ROOT.parent / "repos" / "Perpetua-Tools",
    ):
        if candidate.is_dir() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
    spec = importlib.util.spec_from_file_location("query_peer_topology", _QPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["query_peer_topology"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


@pytest.fixture(scope="module")
def qpt():
    return _load_query_peer_topology()


# ── Bug 1: seed-branch local_node identity ──────────────────────────────


def test_merge_seed_uses_own_hostname_not_peers_self_report(qpt):
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


def test_merge_seed_classifies_pair_not_solo(qpt):
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


def test_merge_second_call_preserves_seeded_local_node(qpt):
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
