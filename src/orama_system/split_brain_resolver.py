"""src/orama_system/split_brain_resolver.py

Split-brain detection and consensus-based resolution (Phase 6).

When peers disagree about each other's reachability, this module resolves
conflicts using a confidence-weighted consensus rule:
  Direct observation > Relayed observation > Stale observation

Where:
  - Direct: I probed it myself (confident)
  - Relayed: Another peer told me (less confident)
  - Stale: Last known state > 15 min old (unreliable)

Design:
  - Merges self-observation with peer reports
  - Confidence scores drive conflict resolution
  - No forced decisions; let freshness convince us
  - Events emitted only on actual disagreement → resolution

Reference: 2026-07-08 self-healing mesh plan § 3.5–3.6
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

__all__ = [
    "PeerObservation",
    "ConsensusResult",
    "resolve_peer_reachability",
    "detect_split_brain",
]

_logger = logging.getLogger(__name__)

# Confidence thresholds
STALE_CONFIDENCE_THRESHOLD = 0.5  # Below this, treat report as unreliable
CONFIDENCE_MIN_REPORT_AGE = 15 * 60  # > 15 min old = stale


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dataclasses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass(frozen=True)
class PeerObservation:
    """A single peer's observation about another peer's reachability.

    Fields:
        observer_id: ID of peer making the observation (e.g., "mac-studio")
        target_id: ID of peer being observed (e.g., "win-rtx3080")
        reachable: Whether observer sees target as reachable
        confidence: Confidence score [0.0–1.0] in this observation
        last_probed: Unix timestamp of last successful probe
        age_seconds: How long ago this observation was made
    """

    observer_id: str
    target_id: str
    reachable: bool
    confidence: float
    last_probed: float
    age_seconds: float

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "observer_id": self.observer_id,
            "target_id": self.target_id,
            "reachable": self.reachable,
            "confidence": self.confidence,
            "last_probed": self.last_probed,
            "age_seconds": self.age_seconds,
        }


@dataclass(frozen=True)
class ConsensusResult:
    """Result of consensus-based conflict resolution.

    Fields:
        target_id: Target peer being resolved
        reachable: Consensus determination
        confidence: Confidence in this determination [0.0–1.0]
        agreement_count: How many observers agree
        disagreement_count: How many observers disagree
        split_brain: True if observations were conflicted
        resolution_reason: Why this decision was made
    """

    target_id: str
    reachable: bool
    confidence: float
    agreement_count: int
    disagreement_count: int
    split_brain: bool
    resolution_reason: str

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "target_id": self.target_id,
            "reachable": self.reachable,
            "confidence": self.confidence,
            "agreement_count": self.agreement_count,
            "disagreement_count": self.disagreement_count,
            "split_brain": self.split_brain,
            "resolution_reason": self.resolution_reason,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Consensus Resolution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def resolve_peer_reachability(
    my_node_id: str,
    my_observation: bool,
    peer_observations: list[PeerObservation],
) -> ConsensusResult:
    """Resolve peer reachability using consensus rule: Direct > Relayed > Stale.

    Args:
        my_node_id: My node identifier (used to identify my direct observation).
        my_observation: My direct observation of target reachability.
        peer_observations: List of other peers' observations (relayed reports).

    Returns:
        ConsensusResult with resolved reachability and confidence.
    """
    if not peer_observations:
        # Only my observation available
        return ConsensusResult(
            target_id="unknown",
            reachable=my_observation,
            confidence=1.0,  # Direct observation is most confident
            agreement_count=1,
            disagreement_count=0,
            split_brain=False,
            resolution_reason="direct_observation_only",
        )

    # Check if peer observations agree or disagree
    peer_agree_count = sum(1 for obs in peer_observations if obs.reachable)
    peer_disagree_count = len(peer_observations) - peer_agree_count
    peer_consensus = peer_agree_count >= peer_disagree_count

    # Calculate average confidence of peer reports
    avg_peer_confidence = sum(obs.confidence for obs in peer_observations) / len(
        peer_observations
    )

    # My direct observation has highest priority
    my_confidence = 1.0

    # Determine consensus based on observations and confidence
    if my_observation == peer_consensus:
        # Agreement: use consensus
        return ConsensusResult(
            target_id=peer_observations[0].target_id,
            reachable=my_observation,
            confidence=min(my_confidence, avg_peer_confidence),
            agreement_count=peer_agree_count + (1 if my_observation else 0),
            disagreement_count=peer_disagree_count + (0 if my_observation else 1),
            split_brain=False,
            resolution_reason="consensus",
        )

    # Disagreement: trust direct over relayed
    if avg_peer_confidence > STALE_CONFIDENCE_THRESHOLD:
        # Peer report is reasonably fresh → might override my stale view
        # But direct observation still wins; just note the disagreement
        return ConsensusResult(
            target_id=peer_observations[0].target_id,
            reachable=my_observation,
            confidence=my_confidence,
            agreement_count=1 if my_observation else peer_agree_count,
            disagreement_count=peer_disagree_count if my_observation else 1,
            split_brain=True,
            resolution_reason="direct_overrides_relayed_due_to_freshness",
        )
    else:
        # Peer report is stale → trust my direct observation
        return ConsensusResult(
            target_id=peer_observations[0].target_id,
            reachable=my_observation,
            confidence=my_confidence,
            agreement_count=1 if my_observation else 0,
            disagreement_count=0 if my_observation else 1,
            split_brain=False,
            resolution_reason="direct_observation_overrides_stale_relayed",
        )


def detect_split_brain(
    target_id: str,
    my_observation: bool,
    peer_observations: list[PeerObservation],
) -> dict:
    """Detect if there's a split-brain condition (observations disagree).

    Split-brain is detected when:
      - My observation differs from peer consensus, AND
      - Peer observation is fresh enough to trust (confidence > threshold)

    Args:
        target_id: Target peer being evaluated.
        my_observation: My direct observation of target.
        peer_observations: Peer observations of target.

    Returns:
        Dict with split_brain (bool), details, and resolution.
    """
    if not peer_observations:
        return {
            "split_brain": False,
            "target_id": target_id,
            "details": "No peer observations available",
        }

    # Check peer consensus
    peer_agree_count = sum(1 for obs in peer_observations if obs.reachable)
    peer_consensus = peer_agree_count >= (len(peer_observations) / 2)

    # Calculate peer confidence
    avg_peer_confidence = sum(obs.confidence for obs in peer_observations) / len(
        peer_observations
    )

    # Split-brain: disagreement with fresh peers
    is_split = (my_observation != peer_consensus) and (
        avg_peer_confidence > STALE_CONFIDENCE_THRESHOLD
    )

    return {
        "split_brain": is_split,
        "target_id": target_id,
        "my_observation": my_observation,
        "peer_consensus": peer_consensus,
        "peer_confidence": avg_peer_confidence,
        "peer_count": len(peer_observations),
        "peer_agree": peer_agree_count,
        "peer_disagree": len(peer_observations) - peer_agree_count,
        "details": f"Split-brain detected: I see {my_observation}, peers consensus {peer_consensus} (confidence {avg_peer_confidence:.2f})"
        if is_split
        else "Consensus reached",
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Multi-Peer Consensus
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def merge_observations(
    my_node_id: str,
    my_topology: dict[str, bool],
    peer_reports: dict[str, dict],
) -> dict[str, ConsensusResult]:
    """Merge my topology observations with peer reports for all peers.

    Args:
        my_node_id: My node identifier.
        my_topology: My direct observations {peer_id: reachable}.
        peer_reports: Peer topology reports {reporter_id: {peer_id: reachable}}.

    Returns:
        Consensus results {peer_id: ConsensusResult} for all peers.
    """
    results = {}

    for peer_id, my_observation in my_topology.items():
        # Collect observations about this peer from others
        observations: list[PeerObservation] = []

        for reporter_id, reporter_topology in peer_reports.items():
            if peer_id in reporter_topology:
                reporter_obs = reporter_topology[peer_id]
                # Create observation (assuming we have confidence data)
                # For now, use a default confidence of 0.8 (high confidence for relayed)
                obs = PeerObservation(
                    observer_id=reporter_id,
                    target_id=peer_id,
                    reachable=reporter_obs.get("reachable", False)
                    if isinstance(reporter_obs, dict)
                    else bool(reporter_obs),
                    confidence=0.8,  # Default for relayed observations
                    last_probed=reporter_obs.get("last_probed", time.time())
                    if isinstance(reporter_obs, dict)
                    else time.time(),
                    age_seconds=reporter_obs.get("age_seconds", 0.0)
                    if isinstance(reporter_obs, dict)
                    else 0.0,
                )
                observations.append(obs)

        # Resolve consensus for this peer
        result = resolve_peer_reachability(my_node_id, my_observation, observations)
        results[peer_id] = result

    return results
