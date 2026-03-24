from __future__ import annotations
"""UserBelief Model — Per-parameter belief with weighted-average update and confidence decay."""

from dataclasses import dataclass, field
from datetime import datetime

from app.models.role_profile import BeliefParameter

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONFIDENCE_CAP: float = 0.95
CONFIDENCE_FLOOR: float = 0.2
CONFIDENCE_DECAY_PER_DAY: float = 0.01


@dataclass(frozen=True)
class UserBelief:
    """
    A single belief about one scheduling parameter for a user.

    Frozen dataclass — all mutations return a new instance.

    Attributes:
        parameter: Which of the 7 belief parameters this tracks.
        belief_value: Current estimated value for the parameter.
        confidence: How confident the system is in this belief (0..1).
        last_updated: When this belief was last updated.
        evidence_count: Number of observations incorporated so far.
    """

    parameter: BeliefParameter
    belief_value: float
    confidence: float = 0.5
    last_updated: datetime = field(default_factory=datetime.now)
    evidence_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, observation: float, signal_weight: float) -> UserBelief:
        """Return a new UserBelief with the observation incorporated via weighted average.

        Formula:
            adjusted_obs = self._adjust_observation(observation)
            new_belief = (old_belief * old_conf + adjusted_obs * weight) / (old_conf + weight)
            new_conf   = min(old_conf + weight * 0.1, CONFIDENCE_CAP)

        For PEAK_ENERGY the result is taken mod 24.
        """
        adjusted_obs = self._adjust_observation(observation)

        new_belief = (
            (self.belief_value * self.confidence + adjusted_obs * signal_weight)
            / (self.confidence + signal_weight)
        )

        if self.parameter == BeliefParameter.PEAK_ENERGY:
            new_belief = new_belief % 24

        new_confidence = min(self.confidence + signal_weight * 0.1, CONFIDENCE_CAP)

        return UserBelief(
            parameter=self.parameter,
            belief_value=new_belief,
            confidence=new_confidence,
            last_updated=datetime.now(),
            evidence_count=self.evidence_count + 1,
        )

    def with_decay(self) -> UserBelief:
        """Return a new UserBelief with confidence decayed based on elapsed time.

        Decay = days_since_last_update * CONFIDENCE_DECAY_PER_DAY, floored at CONFIDENCE_FLOOR.
        """
        now = datetime.now()
        days_since = (now - self.last_updated).total_seconds() / 86400.0
        decayed_confidence = max(
            self.confidence - days_since * CONFIDENCE_DECAY_PER_DAY,
            CONFIDENCE_FLOOR,
        )
        return UserBelief(
            parameter=self.parameter,
            belief_value=self.belief_value,
            confidence=decayed_confidence,
            last_updated=self.last_updated,
            evidence_count=self.evidence_count,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _adjust_observation(self, observation: float) -> float:
        """Handle 24-hour wrapping for PEAK_ENERGY; pass through for all others."""
        if self.parameter != BeliefParameter.PEAK_ENERGY:
            return observation

        diff = abs(self.belief_value - observation)
        if diff > 12:
            # Wrap observation toward the belief across the midnight boundary
            if observation < self.belief_value:
                return observation + 24
            else:
                return observation - 24
        return observation
