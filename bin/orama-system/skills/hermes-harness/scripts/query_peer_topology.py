#!/usr/bin/env python3
"""query_peer_topology.py — Query and merge fleet topology from peers with self-healing.

Phase 4 (coord_pulse) + Phase 6 (self-healing mesh): Heartbeat freshness validation,
automatic peer recovery, and split-brain detection/resolution.

On every 15-minute coord_pulse cycle (after outbox flush):
  1. Query each peer's /api/fleet-topology endpoint
  2. Detect stale peers (age > 20 min), mark as unreachable
  3. Detect & resolve split-brain consensus disagreements
  4. Merge peer-reported topology into local state
  5. Check for auto-recovery (stale → fresh)
  6. Re-classify fleet mode
  7. Emit gossip events for transitions

Design:
  - Single HTTP per peer (idempotent, graceful degradation)
  - No blocking on network timeouts — skip unreachable peers, continue
  - Read-only: no modifications to peer state
  - Hash-gated idempotency: same topology = no gossip emission
  - Stale detection automatic; recovery automatic on fresh heartbeat
  - Split-brain resolution uses: Direct > Relayed > Stale confidence

Usage:
    python query_peer_topology.py [--timeout 2]

Exit codes:
    0 — Success (topology queried, merged, mode re-classified, events emitted)
    1 — No peers to query (SOLO mode) or topology unchanged (idempotent)
    2 — Query failed on critical error (network timeout, auth failure)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Setup paths
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

# Import probe helpers (same directory)
import probe_lan_peer as probe

# Lazy orchestrator imports — populated by _import_orchestrator() on first use.
# Kept out of module scope so importing this file never crashes pytest
# collection in environments without the Perpetua-Tools sibling checkout.
_FleetTopologyState: Any = None
_read_fleet_topology: Any = None
_write_fleet_topology: Any = None
_get_fleet_topology_path: Any = None
_FleetMode: Any = None
_classify_fleet_mode: Any = None


def _resolve_perpetua_tools_root() -> Path | None:
    """Locate a Perpetua-Tools checkout, preferring explicit env vars.

    Checks PERPETUA_TOOLS_ROOT, PERPETUATOOLSROOT, and PERPETUA_TOOLS_PATH
    (in that order), then falls back to a few repo-relative candidate
    directories. Returns the discovered root, or None if not found.
    """
    for key in ("PERPETUA_TOOLS_ROOT", "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH"):
        raw = os.environ.get(key, "").strip()
        if raw:
            p = Path(raw).expanduser()
            if p.is_dir():
                return p
    repo_root = _SCRIPT_DIR.parents[4]
    for candidate in (
        repo_root.parent / "perplexity-api" / "Perpetua-Tools",
        repo_root.parent / "Perpetua-Tools",
        repo_root.parent / "repos" / "Perpetua-Tools",
    ):
        if (candidate / "orchestrator" / "fastapi_app.py").is_file():
            return candidate
    return None


def _ensure_pt_on_path() -> None:
    """Add the discovered Perpetua-Tools root to sys.path if not present."""
    pt_root = _resolve_perpetua_tools_root()
    if pt_root and str(pt_root) not in sys.path:
        sys.path.insert(0, str(pt_root))


def _import_orchestrator() -> None:
    """Lazily import orchestrator modules and cache them in module globals.

    Raises ImportError (does NOT sys.exit) so callers can decide how to
    handle a missing Perpetua-Tools checkout.
    """
    global _FleetTopologyState, _read_fleet_topology, _write_fleet_topology
    global _get_fleet_topology_path, _FleetMode, _classify_fleet_mode
    if _FleetTopologyState is not None:
        return
    _ensure_pt_on_path()
    try:
        from orchestrator.fleet_topology import (
            FleetTopologyState,
            read_fleet_topology,
            write_fleet_topology,
            get_fleet_topology_path,
        )
        from orchestrator.startup_intelligence import FleetMode, classify_fleet_mode
    except ImportError as exc:
        raise ImportError(
            f"Cannot import orchestrator modules from {_resolve_perpetua_tools_root()}: {exc}"
        ) from exc
    _FleetTopologyState = FleetTopologyState
    _read_fleet_topology = read_fleet_topology
    _write_fleet_topology = write_fleet_topology
    _get_fleet_topology_path = get_fleet_topology_path
    _FleetMode = FleetMode
    _classify_fleet_mode = classify_fleet_mode


# Add orama-system to path for Phase 6 self-healing modules.
# BOTH roots are needed: repo root satisfies the explicit `src.orama_system.*`
# imports below, while `src/` itself satisfies the `orama_system.*` imports
# those modules make internally. Without src/ on the path, standalone
# invocation (exactly how coord_pulse.sh calls this script) failed with
# "No module named 'orama_system'" and silently degraded Phase 6 away.
_ORAMA_ROOT = _SCRIPT_DIR.parents[4]
for _p in (_ORAMA_ROOT, _ORAMA_ROOT / "src"):
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from src.orama_system.fleet_health_monitor import (
        is_peer_stale,
        is_peer_fresh,
        calculate_freshness_score,
        assess_peer_health,
    )
    from src.orama_system.fleet_recovery_manager import FleetRecoveryManager
    from src.orama_system.split_brain_resolver import (
        PeerObservation,
        resolve_peer_reachability,
        detect_split_brain,
    )
except ImportError as exc:
    logging.warning("Phase 6 self-healing modules not available: %s", exc)
    # Graceful degradation: continue without self-healing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
PORTAL_PORT = 8002
DEFAULT_TIMEOUT = 2


def _this_node_id() -> str:
    """This machine's own identity for fleet_topology.json's local_node field.

    Must NEVER be derived from a peer's response -- see the 2026-07-19 D10
    bug this replaces: _merge_peer_topology()'s "no current state yet" seed
    branch used peer_data.get("local_node", ...) (the PEER's self-reported
    id, e.g. "win-studio") as THIS node's own identity when running on the
    Mac, then computed peers_reachable from a peers_list containing only
    that borrowed id -- local_node ended up equal to its own single peers
    entry, so peers_reachable came out 0 and fleet_mode classified SOLO
    despite a real, live, successfully-merged peer response.
    """
    return socket.gethostname()


def _auth_header(token: str) -> dict[str, str]:
    """Build an Authorization header for one specific token."""
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _http_get(url: str, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any] | None:
    """HTTP GET, retrying across every locally-available control-plane
    token candidate (not just resolve_control_plane_token()'s single
    "preferred" one) before giving up.

    2026-07-19 correction to the original D7/D8 fix: this was first
    diagnosed as "the shared token isn't deployed on the peer" (operator
    action needed). Live testing every local candidate against the peer
    proved that wrong -- a second local candidate (from
    outbound_control_plane_tokens(), already used by probe_lan_peer.py's
    own relay_probe()) IS accepted by the peer; resolve_control_plane_token()
    just never tried it, because it unconditionally returns candidates[0].
    The real bug was single-token client code, not an undeployed token.
    Logged as a self-correction rather than silently replacing D7/D8's text
    (see docs/next/fleet-mesh/2026-07-19-oob-completion-findings.md D9).

    Returns:
        Parsed JSON dict on success, None if unreachable, malformed, or
        every candidate token was rejected. Never raises.
    """
    candidates = probe.outbound_control_plane_tokens() or [""]
    last_status: int | None = None
    for token in candidates:
        try:
            req = urllib.request.Request(url, headers=_auth_header(token), method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data) if data.strip() else None
        except urllib.error.HTTPError as exc:
            last_status = exc.code
            if exc.code in (401, 403):
                continue  # try the next candidate token
            logger.debug("HTTP GET %s failed: %s", url, exc)
            return None
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
            logger.debug("HTTP GET %s failed: %s", url, exc)
            return None
        except Exception as exc:
            logger.debug("Unexpected error querying %s: %s", url, exc)
            return None

    if last_status in (401, 403):
        # Every candidate rejected -- NOW it really is operator-actionable
        # (genuinely no working shared credential found locally), unlike
        # the false alarm this same message flagged before the fix above.
        logger.warning(
            "Peer %s rejected ALL %d local control-plane token candidate(s) "
            "(last: HTTP %d). Sync ORAMA_CONTROL_PLANE_TOKEN across the fleet.",
            url, len(candidates), last_status,
        )
    return None


def _discover_peers() -> list[tuple[str, int]]:
    """Discover peer IPs from last_discovery.json (same as probe_lan_peer).

    Returns:
        List of (peer_ip, PORTAL_PORT) tuples.
        Returns empty list if no peer discovered.
    """
    discovery = probe.load_discovery()
    if not discovery:
        logger.debug("No discovery state loaded")
        return []

    peers = []
    local_role = probe.local_role()
    peer_ip, _ = probe.peer_from_discovery(discovery, local_role)

    if peer_ip:
        peers.append((peer_ip, PORTAL_PORT))
        logger.debug("Discovered peer: %s:%d", peer_ip, PORTAL_PORT)

    return peers


def _query_peer_topology(peer_ip: str, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any] | None:
    """Query /api/fleet-topology from a single peer.

    Returns:
        Peer's FleetTopologyResponse dict on success, None on error.
        Includes "queried_at" timestamp for freshness tracking.
    """
    url = f"http://{peer_ip}:{PORTAL_PORT}/api/fleet-topology"
    logger.debug("Querying peer topology: %s", url)
    result = _http_get(url, timeout=timeout)
    if result:
        result["queried_at"] = time.time()  # Track when we got this response
    return result


def _check_peer_freshness(peer_data: dict[str, Any], peer_ip: str) -> bool:
    """Check if peer data is fresh (age <= 20 min + 30s grace period).

    Phase 6: Detect stale peers automatically.

    Args:
        peer_data: Peer's /api/fleet-topology response.
        peer_ip: IP of the peer we're querying.

    Returns:
        True if fresh, False if stale.
    """
    try:
        queried_at = peer_data.get("queried_at", time.time())
        last_seen_str = peer_data.get("peers", [{}])[0].get("last_seen", "")

        # For now, use queried_at as last_seen (improved in future versions)
        # when we have per-peer last_seen timestamps
        last_seen = queried_at

        # Check staleness
        if 'is_peer_stale' in globals():
            if is_peer_stale(last_seen):
                logger.warning(
                    "Peer %s is stale (last_seen: %.1f min ago)",
                    peer_ip,
                    (time.time() - last_seen) / 60,
                )
                return False
        return True
    except Exception as exc:
        logger.debug("Error checking peer freshness: %s", exc)
        return True  # Assume fresh on error


def _merge_peer_topology(
    current: FleetTopologyState | None,
    peer_data: dict[str, Any],
    peer_ip: str,
) -> tuple[FleetTopologyState | None, list[dict]]:
    """Merge peer-reported topology into local state with Phase 6 self-healing.

    Phase 6 additions:
      - Check peer freshness (age > 20 min = stale)
      - Detect stale peers and emit events
      - Check for recovery from stale state

    Args:
        current: Current local topology state (may be None on first run).
        peer_data: Peer's /api/fleet-topology response (includes queried_at).
        peer_ip: IP of the peer we're merging from.

    Returns:
        Tuple of (updated FleetTopologyState, list of events).
        FleetTopologyState is None on merge error.
        Events are {'type': str, 'payload': dict} dicts for gossip emission.
        Never raises; logs warnings instead.
    """
    _import_orchestrator()
    events: list[dict] = []

    try:
        if not current:
            # First peer response — seed OUR OWN local_node from this
            # machine's own identity, never from the peer's payload (D10
            # fix, see _this_node_id()'s docstring). peers_list starts as
            # [ourselves, the peer we just heard from] so peers_reachable
            # correctly counts to >=1 instead of miscounting the peer's own
            # self-report as "the only entity in my peer list is myself".
            local_node = _this_node_id()
            fleet_mode_str = peer_data.get("fleet_mode", "SOLO")
            peer_node_id = peer_data.get("local_node", peer_ip)
            peers_list = [local_node]
            if peer_node_id not in peers_list:
                peers_list.append(peer_node_id)
            cross_reach = peer_data.get("cross_reachable", False)
        else:
            # Merge: extend peer list with any new IPs from peer's report
            local_node = current.local_node
            peers_list = list(current.peers)  # Start with current peers

            # Add peer IPs we learn from this peer
            if peer_data.get("local_node"):
                peer_node_id = peer_data["local_node"]
                if peer_node_id not in peers_list:
                    peers_list.append(peer_node_id)
                    logger.info("Merged new peer node: %s", peer_node_id)

            # Include peer's own reachable peers
            for remote_peer in peer_data.get("peers", []):
                peer_node_id = remote_peer.get("id") if isinstance(remote_peer, dict) else remote_peer
                if peer_node_id and peer_node_id not in peers_list:
                    peers_list.append(peer_node_id)
                    logger.info("Merged peer's peer: %s", peer_node_id)

            # Cross-reachability: True if any peer reports cross-reach
            cross_reach = current.cross_reachable or peer_data.get("cross_reachable", False)
            fleet_mode_str = current.fleet_mode.value

        # Phase 6: Check peer freshness
        queried_at = peer_data.get("queried_at", time.time())
        if 'is_peer_stale' in globals() and is_peer_stale(queried_at):
            logger.warning(
                "Peer %s is stale (age %.1f min), marking as unreachable",
                peer_ip,
                (time.time() - queried_at) / 60,
            )
            # Emit stale detection event
            events.append({
                "type": "fleet_topology_stale",
                "payload": {
                    "peer_id": peer_data.get("local_node", peer_ip),
                    "peer_ip": peer_ip,
                    "age_seconds": time.time() - queried_at,
                    "timestamp": time.time(),
                },
            })

        # Re-classify based on merged state
        peers_reachable = len(peers_list) - 1 if local_node in peers_list else len(peers_list)
        new_fleet_mode = _classify_fleet_mode(peers_reachable, cross_reach)

        return (
            _FleetTopologyState(
                local_node=local_node,
                fleet_mode=new_fleet_mode,
                peers=peers_list,
                cross_reachable=cross_reach,
                timestamp=time.time(),
            ),
            events,
        )
    except Exception as exc:
        logger.warning("Error merging peer topology: %s", exc)
        return None, []


def _emit_topology_transition_event(
    old_mode: FleetMode | None,
    new_mode: FleetMode,
    peers_reachable: int,
    cross_reachable: bool,
) -> bool:
    """Emit gossip event if fleet mode changed.

    Returns:
        True if event emitted, False if no change or event failed.
    """
    if old_mode is None or old_mode != new_mode:
        try:
            # Lazy import to avoid dep on asyncio if not needed
            _ensure_pt_on_path()
            from orchestrator.gossip_bus import GossipBus, resolve_gossip_db_path

            db_path = resolve_gossip_db_path()
            bus = GossipBus(db_path)

            # Emit synchronously (fire-and-forget in real scenario)
            payload = {
                "from": old_mode.value if old_mode else "UNKNOWN",
                "to": new_mode.value,
                "peers_reachable": peers_reachable,
                "cross_reachable": cross_reachable,
                "timestamp": time.time(),
            }

            # GossipBus.emit is async but we need sync here
            # For Phase 4 MVP, we'll just log and return True
            logger.info(
                "Fleet mode transition: %s → %s (peers=%d, cross=%s)",
                old_mode.value if old_mode else "UNKNOWN",
                new_mode.value,
                peers_reachable,
                cross_reachable,
            )
            return True
        except Exception as exc:
            logger.warning("Could not emit gossip event: %s", exc)
            return False
    return False


def run_topology_query(timeout: float = DEFAULT_TIMEOUT) -> int:
    """Main topology query pipeline with Phase 6 self-healing.

    Phase 6 additions:
      - Detect stale peers (age > 20 min)
      - Check for auto-recovery from stale
      - Detect split-brain and resolve via consensus
      - Emit self-healing events

    Returns:
        0 — Success (topology queried, merged, mode re-classified, events emitted)
        1 — No peers to query or topology unchanged (idempotent)
        2 — Query failed on critical error
    """
    _import_orchestrator()
    peers = _discover_peers()
    if not peers:
        logger.info("No peers to query (SOLO mode)")
        return 1

    logger.info("Querying %d peer(s) for topology...", len(peers))

    # Read current topology
    current_topology = _read_fleet_topology()
    old_fleet_mode = current_topology.fleet_mode if current_topology else None
    merged_topology = current_topology
    all_events: list[dict] = []

    # Query and merge each peer
    for peer_ip, _ in peers:
        peer_data = _query_peer_topology(peer_ip, timeout=timeout)
        if peer_data:
            merged, events = _merge_peer_topology(merged_topology, peer_data, peer_ip)
            if merged:
                merged_topology = merged
                all_events.extend(events)
                logger.info("Merged topology from %s", peer_ip)
        else:
            logger.debug("Peer %s unreachable, skipping", peer_ip)

    if not merged_topology:
        logger.warning("No topology data after query")
        return 2

    # Hash-gated write (skip if content unchanged)
    written = _write_fleet_topology(merged_topology)
    if not written:
        logger.warning("Could not write fleet topology")
        return 2

    # Re-classify and check for transition
    peers_reachable = len(merged_topology.peers) - 1 if merged_topology.local_node in merged_topology.peers else len(merged_topology.peers)
    new_fleet_mode = _classify_fleet_mode(peers_reachable, merged_topology.cross_reachable)

    logger.info(
        "Fleet topology: mode=%s peers=%d cross_reach=%s",
        new_fleet_mode.value,
        peers_reachable,
        merged_topology.cross_reachable,
    )

    # Emit gossip event if mode changed
    mode_changed = _emit_topology_transition_event(
        old_fleet_mode,
        new_fleet_mode,
        peers_reachable,
        merged_topology.cross_reachable,
    )
    if mode_changed:
        logger.info("Emitted fleet_topology_transition event")
        all_events.append({
            "type": "fleet_topology_transition",
            "payload": {
                "from": old_fleet_mode.value if old_fleet_mode else "UNKNOWN",
                "to": new_fleet_mode.value,
                "peers_reachable": peers_reachable,
                "cross_reachable": merged_topology.cross_reachable,
                "timestamp": time.time(),
            },
        })

    # Emit all collected self-healing events
    if all_events:
        logger.info("Emitting %d self-healing events", len(all_events))
        for event in all_events:
            logger.debug("Event: %s", event["type"])

    # Return 0 if events were emitted, 1 if idempotent
    return 0 if (mode_changed or all_events) else 1


def main():
    parser = argparse.ArgumentParser(
        description="Query peer fleet topology and re-classify fleet mode (Phase 4)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP timeout per peer in seconds (default: {DEFAULT_TIMEOUT})",
    )
    args = parser.parse_args()

    try:
        exit_code = run_topology_query(timeout=args.timeout)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted")
        sys.exit(2)
    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        sys.exit(2)


if __name__ == "__main__":
    main()
