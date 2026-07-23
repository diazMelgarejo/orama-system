"""
display_fleet_status.py — Fleet topology status display helper (Phase 5).

Provides functions to load and format fleet topology state from the cached
fleet_topology.json file. Used by start.sh/start.ps1 for banner display and
the --fleet-status CLI flag.

Design:
- Reads-only from ~/.openclaw/state/fleet_topology.json (no network calls)
- Formats output in multiple styles: banner, JSON, text
- Graceful handling of missing/malformed state
- Safe defaults for all error cases

Reference: Phase 5 deliverables (banner display + CLI flag)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

__all__ = [
    "load_fleet_topology",
    "format_banner",
    "format_json",
    "format_text",
    "get_time_until_next_query",
    "FleetStatusError",
]

_logger = logging.getLogger(__name__)

# 15-minute coord_pulse interval (900 seconds)
COORD_PULSE_INTERVAL_SEC = 900


class FleetStatusError(Exception):
    """Raised when fleet status cannot be determined."""

    pass


def get_fleet_topology_path() -> Path:
    """Return the canonical path to the fleet topology state file."""
    return Path.home() / ".openclaw" / "state" / "fleet_topology.json"


@dataclass
class FleetPeer:
    """Represents a single peer in the fleet."""

    id: str
    ip: str
    port: int
    reachable: bool
    models: list[str]
    last_seen: str  # ISO8601 timestamp


@dataclass
class FleetStatus:
    """Fleet topology status snapshot."""

    fleet_mode: str  # SOLO, PAIR, FLEET
    local_node: str
    peers: list[FleetPeer]
    cross_reachable: bool
    timestamp: float  # Unix timestamp of last topology query
    relay_capable: bool = False

    @property
    def peers_reachable(self) -> int:
        """Number of reachable peers."""
        return sum(1 for p in self.peers if p.reachable)

    @property
    def last_query_iso(self) -> str:
        """Last topology query as ISO8601 string."""
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat()

    @property
    def next_query_in_seconds(self) -> int:
        """Seconds until next coord_pulse query."""
        elapsed = datetime.now(timezone.utc).timestamp() - self.timestamp
        remaining = max(0, COORD_PULSE_INTERVAL_SEC - elapsed)
        return int(remaining)

    @property
    def next_query_formatted(self) -> str:
        """Human-readable time until next query (e.g., '14m 32s')."""
        total_sec = self.next_query_in_seconds
        minutes = total_sec // 60
        seconds = total_sec % 60
        if minutes > 0:
            return f"in {minutes}m {seconds}s"
        return f"in {seconds}s"


def load_fleet_topology(path: Optional[Path] = None) -> Optional[FleetStatus]:
    """Load fleet topology from ~/.openclaw/state/fleet_topology.json.

    Args:
        path: Explicit path to fleet_topology.json (default: standard location)

    Returns:
        FleetStatus on success, None if file doesn't exist or is malformed.
        Never raises; logs warnings instead.
    """
    if path is None:
        path = get_fleet_topology_path()

    if not path.exists():
        _logger.debug(f"Fleet topology file not found at {path}")
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        # Parse peers with safe defaults.
        #
        # 2026-07-19 fix: the canonical writer (PT orchestrator/
        # fleet_topology.py's FleetTopologyState, and orama's own
        # query_peer_topology.py which writes against it) persists
        # `peers` as list[str] -- bare node-id strings, per
        # FleetTopologyState's own docstring ("list of reachable peer
        # identifiers"). This function assumed list[dict] (each entry
        # with id/ip/port/reachable/models/last_seen keys, matching the
        # mother plan's original design-doc example JSON) and crashed
        # with AttributeError on every real merge -- this path had never
        # been exercised against real writer output before. Accept
        # EITHER shape: a bare string becomes a minimal FleetPeer (id
        # only; ip/port/models/last_seen have no data in the flat
        # schema so stay at their safe defaults); a dict still works
        # for any future/richer writer.
        peers_raw = data.get("peers", [])
        this_node = data.get("local_node", "unknown")
        peers = []
        for p in peers_raw:
            # The canonical writer includes this node's own id in `peers`
            # (see FleetTopologyState's merge logic) -- FleetStatus.peers
            # means "the OTHER nodes I see", not "everyone including me";
            # local_node already carries this node's identity separately.
            # Without this exclusion, peers_reachable double-counted this
            # node as its own peer (e.g. "PAIR (2/2 reachable)" for a
            # single real peer).
            if not isinstance(p, (str, dict)):
                _logger.debug("Skipping malformed peer entry: %r", p)
                continue
            entry_id = p if isinstance(p, str) else p.get("id")
            if entry_id == this_node:
                continue
            if isinstance(p, str):
                peer = FleetPeer(
                    id=p,
                    ip="?",
                    port=8002,
                    # Present in the merged peers list at all means the
                    # last merge counted this node as reachable -- the
                    # flat schema doesn't retain a separate per-peer flag.
                    reachable=True,
                    models=[],
                    last_seen="unknown",
                )
            else:
                peer = FleetPeer(
                    id=p.get("id", "unknown"),
                    ip=p.get("ip", "?"),
                    port=p.get("port", 8002),
                    reachable=p.get("reachable", False),
                    models=p.get("models", []),
                    last_seen=p.get("last_seen", "unknown"),
                )
            peers.append(peer)

        status = FleetStatus(
            fleet_mode=data.get("fleet_mode", "SOLO"),
            local_node=data.get("local_node", "unknown"),
            peers=peers,
            cross_reachable=data.get("cross_reachable", False),
            relay_capable=data.get("relay_capable", False),
            timestamp=float(data.get("timestamp", 0.0)),
        )
        return status

    except (ValueError, KeyError, json.JSONDecodeError, OSError) as exc:
        _logger.warning(f"Could not read fleet topology from {path}: {exc}")
        return None


def format_json(status: Optional[FleetStatus]) -> str:
    """Format fleet status as JSON for scripting.

    Args:
        status: FleetStatus or None if unavailable

    Returns:
        JSON string with fleet topology data
    """
    if status is None:
        return json.dumps(
            {
                "fleet_mode": "UNKNOWN",
                "peers_reachable": 0,
                "cross_reachable": False,
                "peers": [],
                "last_query": None,
                "next_query_in_seconds": 0,
                "status": "unavailable",
            }
        )

    peers_data = [
        {
            "id": p.id,
            "ip": p.ip,
            "port": p.port,
            "reachable": p.reachable,
            "models": p.models,
            "last_seen": p.last_seen,
        }
        for p in status.peers
    ]

    result = {
        "fleet_mode": status.fleet_mode,
        "peers_reachable": status.peers_reachable,
        "cross_reachable": status.cross_reachable,
        "relay_capable": status.relay_capable,
        "peers": peers_data,
        "last_query": status.last_query_iso,
        "next_query_in_seconds": status.next_query_in_seconds,
    }
    return json.dumps(result, indent=2)


def format_text(status: Optional[FleetStatus]) -> str:
    """Format fleet status as human-readable text.

    Args:
        status: FleetStatus or None if unavailable

    Returns:
        Human-readable text output
    """
    if status is None:
        return (
            "Fleet Mode: UNAVAILABLE\n"
            "  No fleet topology data found at ~/.openclaw/state/fleet_topology.json\n"
            "  Run: ./start.sh to initialize"
        )

    lines = []
    lines.append(
        f"Fleet Mode: {status.fleet_mode} ({status.peers_reachable}/{len(status.peers)} peers reachable"
        f", cross-reachable={status.cross_reachable})"
    )

    for peer in status.peers:
        mark = "✓" if peer.reachable else "✗"
        models_str = ", ".join(peer.models) if peer.models else "unknown"
        lines.append(f"  {mark} {peer.id} ({peer.ip}) [{models_str}]")

    if not status.peers:
        lines.append("  (no peers)")

    lines.append(f"Last query: {status.last_query_iso}")
    lines.append(f"Next query: {status.next_query_formatted}")

    return "\n".join(lines)


def format_banner(status: Optional[FleetStatus]) -> str:
    """Format fleet status as banner for startup output.

    Args:
        status: FleetStatus or None if unavailable

    Returns:
        Banner string with fleet topology info
    """
    if status is None:
        # SOLO mode default when no state
        return (
            "================================================================================\n"
            "                         FLEET TOPOLOGY STATUS\n"
            "================================================================================\n"
            "Fleet Mode:     SOLO (no topology data)\n"
            "Peer Count:     0/0 reachable\n"
            "Cross-Reachable: N/A\n"
            "Status:         Initializing (run ./start.sh to probe)\n"
            "================================================================================"
        )

    lines = []
    lines.append("=" * 80)
    lines.append(" " * 25 + "FLEET TOPOLOGY STATUS")
    lines.append("=" * 80)

    # Fleet mode line
    cross_str = "YES" if status.cross_reachable else "NO"
    lines.append(f"Fleet Mode:     {status.fleet_mode}")
    lines.append(f"Peer Count:     {status.peers_reachable}/{len(status.peers)} reachable")
    lines.append(f"Cross-Reachable: {cross_str}")

    # Peers section
    if status.peers:
        lines.append("Peers:")
        for peer in status.peers:
            mark = "✓" if peer.reachable else "✗"
            models_str = ", ".join(peer.models) if peer.models else "unknown"
            lines.append(f"  - {peer.id:20s} ({peer.ip:15s}:1234) {mark} models: [{models_str}]")
    else:
        lines.append("Peers: (none)")

    # Timing info
    lines.append(f"Last Topology Query: {status.last_query_iso}")
    lines.append(f"Next Query:          {status.next_query_formatted}")
    lines.append("=" * 80)

    return "\n".join(lines)


def get_time_until_next_query(status: Optional[FleetStatus]) -> int:
    """Get seconds until next coord_pulse topology query.

    Args:
        status: FleetStatus or None

    Returns:
        Number of seconds (0 if unavailable or next query is overdue)
    """
    if status is None:
        return 0
    return status.next_query_in_seconds


if __name__ == "__main__":
    # Quick test
    status = load_fleet_topology()
    print("=== Banner ===")
    print(format_banner(status))
    print("\n=== Text ===")
    print(format_text(status))
    print("\n=== JSON ===")
    print(format_json(status))
