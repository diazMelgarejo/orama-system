"""tests/test_fleet_self_healing.py

Unit tests for Phase 6 (Self-Healing Mesh) components.

Tests cover:
  - Heartbeat freshness validation and scoring
  - Stale detection with grace period
  - Automatic peer recovery
  - Split-brain detection and consensus resolution
  - Integration scenarios

Reference: 2026-07-08 self-healing mesh plan § 4.0–4.6
"""

import time
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.orama_system.fleet_health_monitor import (
    calculate_freshness_score,
    is_peer_stale,
    is_peer_fresh,
    assess_peer_health,
    FRESHNESS_WINDOW_SECONDS,
    FRESH_THRESHOLD_SECONDS,
    RECENT_THRESHOLD_SECONDS,
    STALE_THRESHOLD_SECONDS,
    GRACE_PERIOD_SECONDS,
)
from src.orama_system.fleet_recovery_manager import (
    FleetRecoveryManager,
    PeerRecoveryState,
)
from src.orama_system.split_brain_resolver import (
    PeerObservation,
    resolve_peer_reachability,
    detect_split_brain,
    ConsensusResult,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: Freshness Scoring
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFreshnessScoring:
    """Test freshness score calculation across all tiers."""

    def test_fresh_score_less_than_5_min(self):
        """< 5 min should have score = 1.0 (fresh)."""
        age_4_min = 4 * 60  # 240 seconds
        score = calculate_freshness_score(age_4_min)
        assert score == 1.0, "Score should be 1.0 for age < 5 min"

    def test_recent_score_between_5_and_15_min(self):
        """5-15 min should have score between 0.8 and 0.98 (linear interpolation)."""
        age_10_min = 10 * 60  # 600 seconds
        score = calculate_freshness_score(age_10_min)
        assert 0.8 < score < 0.98, f"Score should be between 0.8 and 0.98, got {score}"
        # Exact check: 0.8 + (900 - 600) / 3000 = 0.8 + 0.1 = 0.9
        assert abs(score - 0.9) < 0.001

    def test_stale_score_between_15_and_20_min(self):
        """15-20 min should have score = 0.4 (stale)."""
        age_18_min = 18 * 60  # 1080 seconds
        score = calculate_freshness_score(age_18_min)
        assert score == 0.4, f"Score should be 0.4, got {score}"

    def test_expired_score_greater_than_20_min(self):
        """> 20 min should have score = 0.0 (expired)."""
        age_25_min = 25 * 60  # 1500 seconds
        score = calculate_freshness_score(age_25_min)
        assert score == 0.0, f"Score should be 0.0, got {score}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: Stale Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestStaleDetection:
    """Test stale peer detection with grace period."""

    def test_fresh_peer_not_stale(self):
        """Peer age < 5 min should not be stale."""
        now = time.time()
        last_seen = now - (3 * 60)  # 3 minutes ago
        assert not is_peer_stale(last_seen)

    def test_peer_at_grace_boundary_not_stale(self):
        """Peer at 20 min + grace period boundary should not be stale."""
        now = time.time()
        # 20 min + 30 sec (grace period)
        last_seen = now - (FRESHNESS_WINDOW_SECONDS + GRACE_PERIOD_SECONDS - 1)
        assert not is_peer_stale(last_seen)

    def test_stale_peer_detected(self):
        """Peer age > 20 min + grace period should be stale."""
        now = time.time()
        # 20 min + 30 sec + 1 second (definitely stale)
        last_seen = now - (FRESHNESS_WINDOW_SECONDS + GRACE_PERIOD_SECONDS + 1)
        assert is_peer_stale(last_seen)

    def test_future_timestamp_not_stale(self):
        """Future timestamp (clock skew) should not be stale."""
        now = time.time()
        last_seen = now + (5 * 60)  # 5 minutes in the future
        assert not is_peer_stale(last_seen)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: Fresh Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFreshDetection:
    """Test fresh peer detection."""

    def test_peer_with_recent_heartbeat_is_fresh(self):
        """Peer with heartbeat < 5 min old should be fresh."""
        now = time.time()
        last_seen = now - (2 * 60)  # 2 minutes ago
        assert is_peer_fresh(last_seen)

    def test_peer_at_5_min_boundary_not_fresh(self):
        """Peer at 5 min boundary should not be fresh."""
        now = time.time()
        last_seen = now - FRESH_THRESHOLD_SECONDS
        assert not is_peer_fresh(last_seen)

    def test_stale_peer_not_fresh(self):
        """Stale peer should definitely not be fresh."""
        now = time.time()
        last_seen = now - (30 * 60)  # 30 minutes ago
        assert not is_peer_fresh(last_seen)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: Peer Health Assessment
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPeerHealthAssessment:
    """Test peer health snapshots."""

    def test_fresh_peer_health(self):
        """Fresh peer should have high freshness score and not be stale."""
        now = time.time()
        last_seen = now - (2 * 60)  # 2 minutes ago
        health = assess_peer_health("win-rtx3080", last_seen, reachable=True)

        assert health.peer_id == "win-rtx3080"
        assert health.freshness_score == 1.0
        assert not health.is_stale
        assert health.reachable

    def test_stale_peer_health(self):
        """Stale peer should have zero freshness score and is_stale=True."""
        now = time.time()
        last_seen = now - (25 * 60)  # 25 minutes ago
        health = assess_peer_health("win-rtx3080", last_seen, reachable=False)

        assert health.peer_id == "win-rtx3080"
        assert health.freshness_score == 0.0
        assert health.is_stale
        assert not health.reachable

    def test_peer_health_to_dict(self):
        """Peer health should serialize to dict."""
        now = time.time()
        last_seen = now - (10 * 60)
        health = assess_peer_health("mac-studio", last_seen, reachable=True)
        d = health.to_dict()

        assert isinstance(d, dict)
        assert d["peer_id"] == "mac-studio"
        assert d["reachable"]
        assert "freshness_score" in d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: Automatic Recovery
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestAutomaticRecovery:
    """Test automatic peer recovery from stale state."""

    @pytest.mark.asyncio
    async def test_fresh_to_stale_transition(self):
        """Peer going from fresh to stale should emit event."""
        with TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recovery.json"
            manager = FleetRecoveryManager(state_file)
            await manager.init()

            now = time.time()

            # First: peer is fresh
            fresh_last_seen = now - (2 * 60)  # 2 minutes ago
            events = await manager.update_peer("win-rtx3080", is_stale=False, last_seen=fresh_last_seen)
            assert len(events) == 0, "No event when peer first appears fresh"

            # Second: peer becomes stale
            stale_last_seen = now - (25 * 60)  # 25 minutes ago
            events = await manager.update_peer("win-rtx3080", is_stale=True, last_seen=stale_last_seen)
            assert len(events) == 1, "Should emit stale event"
            assert events[0]["type"] == "fleet_topology_stale"
            assert events[0]["payload"]["peer_id"] == "win-rtx3080"

    @pytest.mark.asyncio
    async def test_stale_to_recovered_transition(self):
        """Peer recovering from stale should emit recovery event."""
        with TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recovery.json"
            manager = FleetRecoveryManager(state_file)
            await manager.init()

            now = time.time()

            # First: peer becomes stale
            stale_last_seen = now - (25 * 60)
            events = await manager.update_peer("win-rtx3080", is_stale=True, last_seen=stale_last_seen)
            assert len(events) == 1  # Stale event
            assert events[0]["type"] == "fleet_topology_stale"

            # Second: peer recovers (becomes fresh again)
            fresh_last_seen = now - (2 * 60)
            events = await manager.update_peer("win-rtx3080", is_stale=False, last_seen=fresh_last_seen)
            assert len(events) == 1, "Should emit recovery event"
            assert events[0]["type"] == "fleet_topology_recovered"
            assert "stale_duration" in events[0]["payload"]

    @pytest.mark.asyncio
    async def test_idempotent_stale_state(self):
        """Peer staying stale should not emit repeated events."""
        with TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recovery.json"
            manager = FleetRecoveryManager(state_file)
            await manager.init()

            now = time.time()

            # First: peer is stale
            stale_last_seen = now - (25 * 60)
            events = await manager.update_peer("win-rtx3080", is_stale=True, last_seen=stale_last_seen)
            assert len(events) == 1  # Stale event

            # Second: peer stays stale
            stale_last_seen2 = now - (30 * 60)
            events = await manager.update_peer("win-rtx3080", is_stale=True, last_seen=stale_last_seen2)
            assert len(events) == 0, "No event when peer stays stale (idempotent)"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: Split-Brain Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSplitBrainDetection:
    """Test split-brain scenario detection."""

    def test_no_split_brain_with_agreement(self):
        """When all agree on reachability, no split-brain."""
        my_obs = True
        peer_obs = [
            PeerObservation("3080", "mac-studio", True, 0.9, time.time(), 0),
        ]
        result = detect_split_brain("mac-studio", my_obs, peer_obs)

        assert not result["split_brain"]
        assert result["peer_consensus"] == True

    def test_split_brain_detected_with_disagreement(self):
        """When I see UP but peers see DOWN, split-brain is detected."""
        my_obs = True
        peer_obs = [
            PeerObservation("3080", "mac-studio", False, 0.8, time.time(), 0),
        ]
        result = detect_split_brain("mac-studio", my_obs, peer_obs)

        assert result["split_brain"]  # Disagreement with fresh peers
        assert my_obs != result["peer_consensus"]

    def test_no_split_brain_with_stale_peers(self):
        """When disagreement is with stale peers, no split-brain reported."""
        my_obs = True
        peer_obs = [
            PeerObservation("3080", "mac-studio", False, 0.2, time.time() - (20 * 60), 20 * 60),  # Stale
        ]
        result = detect_split_brain("mac-studio", my_obs, peer_obs)

        # Disagreement but with stale peers → not a true split-brain
        assert not result["split_brain"] or result["peer_confidence"] < 0.5

    def test_no_peer_observations(self):
        """When no peer observations, no split-brain."""
        my_obs = True
        result = detect_split_brain("mac-studio", my_obs, [])

        assert not result["split_brain"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: Split-Brain Consensus Resolution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConsensusResolution:
    """Test split-brain resolution via consensus rule."""

    def test_direct_observation_only(self):
        """Direct observation (no peers) should have highest confidence."""
        result = resolve_peer_reachability("mac-studio", True, [])

        assert result.reachable == True
        assert result.confidence == 1.0
        assert result.resolution_reason == "direct_observation_only"

    def test_direct_overrides_stale_relayed(self):
        """Direct observation overrides stale peer reports."""
        my_obs = True
        peer_obs = [
            PeerObservation("3080", "mac-studio", False, 0.2, time.time() - (20 * 60), 20 * 60),
        ]
        result = resolve_peer_reachability("mac-studio", my_obs, peer_obs)

        assert result.reachable == True  # My observation wins
        assert result.confidence == 1.0  # Direct is most confident

    def test_consensus_when_no_disagreement(self):
        """When my observation matches peer consensus, use consensus."""
        my_obs = True
        peer_obs = [
            PeerObservation("3080", "mac-studio", True, 0.9, time.time(), 0),
            PeerObservation("3070", "mac-studio", True, 0.9, time.time(), 0),
        ]
        result = resolve_peer_reachability("mac-studio", my_obs, peer_obs)

        assert result.reachable == True
        assert result.split_brain == False

    def test_multiple_peer_consensus(self):
        """Consensus from multiple peers should affect confidence."""
        my_obs = False
        peer_obs = [
            PeerObservation("3080", "mac-studio", True, 0.85, time.time(), 0),
            PeerObservation("3070", "mac-studio", True, 0.85, time.time(), 0),
            PeerObservation("oldmac", "mac-studio", False, 0.3, time.time() - (20 * 60), 20 * 60),
        ]
        result = resolve_peer_reachability("mac-studio", my_obs, peer_obs)

        # 2 fresh peers say True, 1 stale says False, I say False
        # Consensus is probably True (2 vs 1 fresh), but direct still wins
        assert result.reachable == my_obs  # Direct wins
        assert result.split_brain or result.resolution_reason == "direct_overrides_relayed_due_to_freshness"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Integration Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestIntegration:
    """Integration tests combining multiple Phase 6 components."""

    @pytest.mark.asyncio
    async def test_full_stale_to_recovery_cycle(self):
        """Full cycle: fresh → stale detection → recovery."""
        with TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recovery.json"
            manager = FleetRecoveryManager(state_file)
            await manager.init()

            now = time.time()
            peer_id = "win-rtx3080"

            # Phase 1: Peer is fresh
            fresh_last_seen = now - (2 * 60)
            health1 = assess_peer_health(peer_id, fresh_last_seen, True)
            assert not health1.is_stale
            events = await manager.update_peer(peer_id, health1.is_stale, fresh_last_seen)
            assert len(events) == 0

            # Phase 2: Peer becomes stale
            stale_last_seen = now - (25 * 60)
            health2 = assess_peer_health(peer_id, stale_last_seen, False)
            assert health2.is_stale
            events = await manager.update_peer(peer_id, health2.is_stale, stale_last_seen)
            assert len(events) == 1
            assert events[0]["type"] == "fleet_topology_stale"

            # Phase 3: Peer recovers
            recovered_last_seen = now - (1 * 60)
            health3 = assess_peer_health(peer_id, recovered_last_seen, True)
            assert not health3.is_stale
            events = await manager.update_peer(peer_id, health3.is_stale, recovered_last_seen)
            assert len(events) == 1
            assert events[0]["type"] == "fleet_topology_recovered"

    def test_split_brain_and_resolution(self):
        """Split-brain scenario with resolution."""
        # Scenario: I see mac-studio as UP, but 3080 (via relay) sees it as DOWN
        # Fresh peers should influence resolution
        my_obs = True
        peer_obs = [
            PeerObservation("win-3080", "mac-studio", False, 0.7, time.time(), 0),  # Fresh, says DOWN
        ]

        # Run split-brain detection
        split_result = detect_split_brain("mac-studio", my_obs, peer_obs)
        assert split_result["split_brain"]  # We have disagreement

        # Run consensus resolution
        consensus = resolve_peer_reachability("mac-studio", my_obs, peer_obs)
        # Direct observation should win
        assert consensus.reachable == my_obs
        assert consensus.confidence == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
