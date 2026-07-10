"""src/orama_system/fleet_recovery_manager.py

Automatic peer recovery and stale detection (Phase 6).

Tracks peer state transitions (fresh → stale → recovered) and emits gossip
events on actual changes. Recovery is automatic: once a stale peer responds
fresh again, it's marked recovered and events are emitted.

Design:
  - Recovery flow: Stale (age > 20 min) → emit event → Wait → Fresh → Recovered → emit event
  - Idempotent: same state = no events
  - No gossip noise: events only on actual transitions
  - Peer state persisted to enable recovery across restarts

Reference: 2026-07-08 self-healing mesh plan § 3.3–3.4
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

__all__ = [
    "PeerRecoveryState",
    "FleetRecoveryManager",
]

_logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dataclass
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass(frozen=True)
class PeerRecoveryState:
    """Immutable peer recovery state snapshot.

    Fields:
        peer_id: Peer node identifier
        is_stale: True if peer is currently stale (age > 20 min)
        stale_since: Unix timestamp when peer first entered stale state
        stale_duration_seconds: How long peer has been stale
        recovered: True if peer recovered from stale state
        last_recovery: Unix timestamp of most recent recovery (if recovered)
    """

    peer_id: str
    is_stale: bool
    stale_since: Optional[float]
    stale_duration_seconds: float
    recovered: bool
    last_recovery: Optional[float]

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "peer_id": self.peer_id,
            "is_stale": self.is_stale,
            "stale_since": self.stale_since,
            "stale_duration_seconds": self.stale_duration_seconds,
            "recovered": self.recovered,
            "last_recovery": self.last_recovery,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FleetRecoveryManager
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class FleetRecoveryManager:
    """Tracks peer recovery state and emits transitions.

    This manager maintains a state file tracking which peers are stale and
    when they entered that state. On topology queries, we update peer status
    and check for transitions (fresh → stale or stale → recovered).

    Usage:
        manager = FleetRecoveryManager(state_file)
        await manager.init()

        # After topology query:
        health = assess_peer_health(peer_id, last_seen, reachable)
        events = await manager.update_peer(health)
        for event in events:
            await gossip_bus.emit(event["type"], event["payload"])

    State file format (JSON):
        {
            "peers": {
                "win-rtx3080": {
                    "is_stale": false,
                    "stale_since": null,
                    "stale_duration": 0.0,
                    "last_recovery": 1720488000.0
                }
            }
        }
    """

    def __init__(self, state_file: Path | str | None = None):
        """Initialize recovery manager.

        Args:
            state_file: Path to persistent recovery state file.
                       If None, uses ~/.openclaw/state/fleet_recovery.json
        """
        if state_file is None:
            state_dir = Path.home() / ".openclaw" / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            self._state_file = state_dir / "fleet_recovery.json"
        else:
            self._state_file = Path(state_file)
        self._peer_states: dict[str, dict] = {}

    async def init(self) -> None:
        """Load recovery state from disk (idempotent)."""
        self._load_state()

    def _load_state(self) -> None:
        """Load peer recovery state from disk."""
        if not self._state_file.exists():
            self._peer_states = {}
            return

        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            self._peer_states = data.get("peers", {})
            _logger.debug(f"Loaded recovery state for {len(self._peer_states)} peers")
        except Exception as exc:
            _logger.warning(f"Could not load recovery state from {self._state_file}: {exc}")
            self._peer_states = {}

    def _save_state(self) -> bool:
        """Save peer recovery state to disk.

        Returns:
            True if written successfully, False on error.
        """
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {"peers": self._peer_states}
            self._state_file.write_text(
                json.dumps(data, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            return True
        except Exception as exc:
            _logger.warning(f"Could not save recovery state to {self._state_file}: {exc}")
            return False

    async def update_peer(self, peer_id: str, is_stale: bool, last_seen: float) -> list[dict]:
        """Update peer status and return transition events.

        Args:
            peer_id: Peer node identifier.
            is_stale: Whether peer is currently stale (age > 20 min).
            last_seen: Unix timestamp of last successful contact.

        Returns:
            List of gossip events to emit (empty if no transition).
            Each event is {"type": str, "payload": dict}.
        """
        events: list[dict] = []
        now = time.time()
        old_state = self._peer_states.get(peer_id, {})
        old_is_stale = old_state.get("is_stale", False)
        old_stale_since = old_state.get("stale_since")

        # Transition: fresh → stale
        if is_stale and not old_is_stale:
            self._peer_states[peer_id] = {
                "is_stale": True,
                "stale_since": now,
                "stale_duration": 0.0,
                "last_recovery": old_state.get("last_recovery"),
            }
            events.append({
                "type": "fleet_topology_stale",
                "payload": {
                    "peer_id": peer_id,
                    "stale_since": now,
                    "age_seconds": now - last_seen,
                    "timestamp": now,
                },
            })
            _logger.warning(f"Peer {peer_id} marked stale (age > 20 min)")

        # Transition: stale → recovered
        elif not is_stale and old_is_stale and old_stale_since is not None:
            stale_duration = now - old_stale_since
            self._peer_states[peer_id] = {
                "is_stale": False,
                "stale_since": None,
                "stale_duration": stale_duration,
                "last_recovery": now,
            }
            events.append({
                "type": "fleet_topology_recovered",
                "payload": {
                    "peer_id": peer_id,
                    "stale_duration": stale_duration,
                    "age_seconds": now - last_seen,
                    "timestamp": now,
                },
            })
            _logger.info(
                f"Peer {peer_id} recovered from stale (was stale for {stale_duration:.0f}s)"
            )

        # Update stale_duration if still stale
        elif is_stale and old_is_stale and old_stale_since is not None:
            stale_duration = now - old_stale_since
            self._peer_states[peer_id] = {
                "is_stale": True,
                "stale_since": old_stale_since,
                "stale_duration": stale_duration,
                "last_recovery": old_state.get("last_recovery"),
            }
            # No event emitted (idempotent: already stale)

        # No change
        else:
            if peer_id not in self._peer_states:
                self._peer_states[peer_id] = {
                    "is_stale": is_stale,
                    "stale_since": now if is_stale else None,
                    "stale_duration": 0.0,
                    "last_recovery": None,
                }

        # Persist state
        self._save_state()

        return events

    def get_peer_recovery_state(self, peer_id: str) -> PeerRecoveryState:
        """Get immutable snapshot of peer recovery state.

        Args:
            peer_id: Peer node identifier.

        Returns:
            PeerRecoveryState snapshot.
        """
        state = self._peer_states.get(peer_id, {})
        is_stale = state.get("is_stale", False)
        stale_since = state.get("stale_since")
        now = time.time()
        stale_duration = (now - stale_since) if stale_since else 0.0

        return PeerRecoveryState(
            peer_id=peer_id,
            is_stale=is_stale,
            stale_since=stale_since,
            stale_duration_seconds=stale_duration,
            recovered=state.get("last_recovery") is not None,
            last_recovery=state.get("last_recovery"),
        )
