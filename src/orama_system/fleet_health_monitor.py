"""src/orama_system/fleet_health_monitor.py

Fleet health monitoring with heartbeat freshness validation (Phase 6).

Tracks peer freshness by age, calculates freshness scores, detects stale peers,
and manages grace periods for clock skew. All thresholds are constants defined
in this module and never hardcoded elsewhere.

Design:
  - 20-minute freshness window (hard rule, no exceptions)
  - ±30 second clock skew grace period
  - Freshness score: 1.0 (fresh) → 0.4 (stale) → 0.0 (expired)
  - Never crashes on missing data; logs warnings instead
  - Idempotent: same state = no changes = no events

Reference: 2026-07-08 self-healing mesh plan § 3.1–3.2
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

__all__ = [
    "FRESHNESS_WINDOW_SECONDS",
    "GRACE_PERIOD_SECONDS",
    "FRESH_THRESHOLD_SECONDS",
    "RECENT_THRESHOLD_SECONDS",
    "STALE_THRESHOLD_SECONDS",
    "FleetPeerHealth",
    "calculate_freshness_score",
    "is_peer_stale",
    "is_peer_fresh",
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants (all freshness thresholds)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FRESHNESS_WINDOW_SECONDS = 20 * 60  # 20 minutes (hard rule)
GRACE_PERIOD_SECONDS = 30  # ±30 seconds for clock skew
FRESH_THRESHOLD_SECONDS = 5 * 60  # < 5 min → fresh (score 1.0)
RECENT_THRESHOLD_SECONDS = 15 * 60  # 5-15 min → recent (score 0.8–0.98)
STALE_THRESHOLD_SECONDS = 20 * 60  # 15-20 min → stale (score 0.4)

_logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dataclass
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass(frozen=True)
class FleetPeerHealth:
    """Immutable snapshot of a peer's health state.

    Fields:
        peer_id: Peer node identifier
        last_seen: Unix timestamp (float) of last successful contact
        reachable: Whether peer is currently marked reachable
        freshness_score: Calculated score [0.0–1.0]
        is_stale: True if age > 20 min (excluding grace period)
        age_seconds: Age in seconds since last_seen
    """

    peer_id: str
    last_seen: float
    reachable: bool
    freshness_score: float
    is_stale: bool
    age_seconds: float

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "peer_id": self.peer_id,
            "last_seen": self.last_seen,
            "reachable": self.reachable,
            "freshness_score": self.freshness_score,
            "is_stale": self.is_stale,
            "age_seconds": self.age_seconds,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Freshness Calculation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def calculate_freshness_score(age_seconds: float) -> float:
    """Calculate a freshness score [0.0–1.0] based on age.

    Scoring tiers:
      - < 5 min (300s): score = 1.0 (fresh)
      - 5-15 min (300–900s): score = 0.8 + (900 - age) / 3000
      - 15-20 min (900–1200s): score = 0.4
      - > 20 min (1200s+): score = 0.0 (expired)

    Args:
        age_seconds: Age in seconds since last successful contact.

    Returns:
        Freshness score in [0.0, 1.0].
    """
    if age_seconds < FRESH_THRESHOLD_SECONDS:
        return 1.0
    elif age_seconds < RECENT_THRESHOLD_SECONDS:
        # Linear interpolation from 0.8 to 0.98 over 10-minute window
        return 0.8 + (RECENT_THRESHOLD_SECONDS - age_seconds) / 3000
    elif age_seconds < STALE_THRESHOLD_SECONDS:
        return 0.4
    else:
        return 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Stale Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def is_peer_stale(last_seen: float, grace_seconds: float = GRACE_PERIOD_SECONDS) -> bool:
    """Check if a peer's heartbeat is stale (age > 20 min + grace period).

    Args:
        last_seen: Unix timestamp of last successful contact.
        grace_seconds: Grace period for clock skew (default: 30 seconds).

    Returns:
        True if age > (20 min + grace period), False otherwise.
        Never raises; returns False if last_seen is in the future (clock skew).
    """
    age_seconds = time.time() - last_seen
    if age_seconds < 0:
        # Future timestamp (clock skew) — treat as fresh
        _logger.debug(f"Peer timestamp is in future by {-age_seconds:.1f}s (clock skew)")
        return False
    freshness_window_with_grace = FRESHNESS_WINDOW_SECONDS + grace_seconds
    return age_seconds > freshness_window_with_grace


def is_peer_fresh(last_seen: float) -> bool:
    """Check if a peer's heartbeat is fresh (age < 5 min).

    Args:
        last_seen: Unix timestamp of last successful contact.

    Returns:
        True if age < 5 minutes, False otherwise.
        Never raises; returns False if last_seen is in the future.
    """
    age_seconds = time.time() - last_seen
    if age_seconds < 0:
        return False
    return age_seconds < FRESH_THRESHOLD_SECONDS


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Health Assessment
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def assess_peer_health(
    peer_id: str,
    last_seen: float,
    reachable: bool,
) -> FleetPeerHealth:
    """Assess current health of a single peer.

    Args:
        peer_id: Peer node identifier.
        last_seen: Unix timestamp of last successful contact.
        reachable: Whether peer is marked reachable in topology.

    Returns:
        FleetPeerHealth snapshot (immutable).
    """
    age_seconds = time.time() - last_seen
    age_seconds = max(0.0, age_seconds)  # Clamp to 0 on clock skew

    freshness_score = calculate_freshness_score(age_seconds)
    is_stale = is_peer_stale(last_seen)

    return FleetPeerHealth(
        peer_id=peer_id,
        last_seen=last_seen,
        reachable=reachable,
        freshness_score=freshness_score,
        is_stale=is_stale,
        age_seconds=age_seconds,
    )
