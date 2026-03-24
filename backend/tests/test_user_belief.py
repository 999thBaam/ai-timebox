from __future__ import annotations
"""Tests for UserBelief model with weighted-average update and confidence decay."""

from datetime import datetime, timedelta

from app.models.role_profile import BeliefParameter
from app.models.user_belief import (
    CONFIDENCE_CAP,
    CONFIDENCE_DECAY_PER_DAY,
    CONFIDENCE_FLOOR,
    UserBelief,
)


class TestUserBeliefCreation:
    """Tests for creating a UserBelief instance."""

    def test_create_belief(self) -> None:
        """Create a belief with explicit parameter, value, confidence, and evidence_count."""
        belief = UserBelief(
            parameter=BeliefParameter.PEAK_ENERGY,
            belief_value=22.0,
            confidence=0.5,
            evidence_count=0,
        )
        assert belief.parameter == BeliefParameter.PEAK_ENERGY
        assert belief.belief_value == 22.0
        assert belief.confidence == 0.5
        assert belief.evidence_count == 0


class TestUserBeliefUpdate:
    """Tests for the weighted-average update logic."""

    def test_update_simple(self) -> None:
        """CHAOS_TOLERANCE belief 0.4, conf 0.5, update with obs=0.7, weight=0.3.

        new_belief = (0.4 * 0.5 + 0.7 * 0.3) / (0.5 + 0.3) = 0.41 / 0.8 = 0.5125
        new_conf   = min(0.5 + 0.3 * 0.1, 0.95) = 0.53
        evidence_count = 0 + 1 = 1
        """
        belief = UserBelief(
            parameter=BeliefParameter.CHAOS_TOLERANCE,
            belief_value=0.4,
            confidence=0.5,
            evidence_count=0,
        )
        updated = belief.update(observation=0.7, signal_weight=0.3)
        assert abs(updated.belief_value - 0.5125) < 1e-6
        assert abs(updated.confidence - 0.53) < 1e-6
        assert updated.evidence_count == 1

    def test_update_peak_energy_wrapping(self) -> None:
        """PEAK_ENERGY belief 23.0, conf 0.5, obs=1.0, weight=0.3.

        abs(23.0 - 1.0) = 22 > 12, so obs adjusted to 1.0 + 24 = 25.0
        new_belief = (23.0 * 0.5 + 25.0 * 0.3) / (0.5 + 0.3) = 19.0 / 0.8 = 23.75
        Result mod 24 = 23.75 (no change needed since < 24)
        """
        belief = UserBelief(
            parameter=BeliefParameter.PEAK_ENERGY,
            belief_value=23.0,
            confidence=0.5,
            evidence_count=0,
        )
        updated = belief.update(observation=1.0, signal_weight=0.3)
        assert abs(updated.belief_value - 23.75) < 1e-6

    def test_update_peak_energy_no_wrapping(self) -> None:
        """PEAK_ENERGY belief 14.0, obs=16.0, weight=0.3.

        abs(14.0 - 16.0) = 2 <= 12, no adjustment needed.
        new_belief = (14.0 * 0.5 + 16.0 * 0.3) / (0.5 + 0.3) = 11.8 / 0.8 = 14.75
        """
        belief = UserBelief(
            parameter=BeliefParameter.PEAK_ENERGY,
            belief_value=14.0,
            confidence=0.5,
            evidence_count=0,
        )
        updated = belief.update(observation=16.0, signal_weight=0.3)
        assert abs(updated.belief_value - 14.75) < 1e-6

    def test_confidence_cap(self) -> None:
        """Starting conf 0.94, update should not exceed CONFIDENCE_CAP (0.95)."""
        belief = UserBelief(
            parameter=BeliefParameter.DEEP_WORK_TOLERANCE,
            belief_value=60.0,
            confidence=0.94,
            evidence_count=5,
        )
        updated = belief.update(observation=65.0, signal_weight=0.3)
        assert updated.confidence <= CONFIDENCE_CAP
        assert abs(updated.confidence - 0.95) < 1e-6


class TestUserBeliefDecay:
    """Tests for confidence decay over time."""

    def test_confidence_decay(self) -> None:
        """Conf 0.8, last_updated 5 days ago, decay=0.01/day -> conf ~= 0.75."""
        five_days_ago = datetime.now() - timedelta(days=5)
        belief = UserBelief(
            parameter=BeliefParameter.RECOVERY_RATE,
            belief_value=0.12,
            confidence=0.8,
            last_updated=five_days_ago,
            evidence_count=3,
        )
        decayed = belief.with_decay()
        assert abs(decayed.confidence - 0.75) < 1e-6

    def test_confidence_floor(self) -> None:
        """Conf 0.22, 10 days decay -> 0.22 - 0.10 = 0.12, but floor at 0.2."""
        ten_days_ago = datetime.now() - timedelta(days=10)
        belief = UserBelief(
            parameter=BeliefParameter.MEETING_TOLERANCE,
            belief_value=0.5,
            confidence=0.22,
            last_updated=ten_days_ago,
            evidence_count=1,
        )
        decayed = belief.with_decay()
        assert abs(decayed.confidence - CONFIDENCE_FLOOR) < 1e-6


class TestUserBeliefImmutability:
    """Tests that update returns a new object and original is unchanged."""

    def test_immutability(self) -> None:
        """update() returns new object, original unchanged."""
        original = UserBelief(
            parameter=BeliefParameter.CHAOS_TOLERANCE,
            belief_value=0.4,
            confidence=0.5,
            evidence_count=0,
        )
        updated = original.update(observation=0.7, signal_weight=0.3)

        # Original should be unchanged
        assert original.belief_value == 0.4
        assert original.confidence == 0.5
        assert original.evidence_count == 0

        # Updated should be different
        assert updated is not original
        assert updated.belief_value != original.belief_value
        assert updated.confidence != original.confidence
        assert updated.evidence_count == 1
