"""Tests for CheckInGenerator — weekly lowest-confidence check-in service."""

from __future__ import annotations

from typing import Dict, Optional

import pytest

from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief
from app.services.checkin_generator import CheckInGenerator


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_beliefs(
    confidences: Optional[Dict[BeliefParameter, float]] = None,
    default_confidence: float = 0.5,
) -> Dict[BeliefParameter, UserBelief]:
    """Create a full dict of 7 BeliefParameter -> UserBelief.

    Every belief gets belief_value=0.5 and the specified confidence.
    Override individual confidences via the *confidences* mapping.
    """
    overrides = confidences or {}
    return {
        param: UserBelief(
            parameter=param,
            belief_value=0.5,
            confidence=overrides.get(param, default_confidence),
        )
        for param in BeliefParameter
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckInGenerator:
    """CheckInGenerator.generate() test suite."""

    def test_picks_lowest_confidence(self):
        """When deep_work has the lowest confidence (0.3), it should be selected."""
        beliefs = _make_beliefs(
            confidences={
                BeliefParameter.DEEP_WORK_TOLERANCE: 0.3,
                BeliefParameter.PEAK_ENERGY: 0.6,
                BeliefParameter.CHAOS_TOLERANCE: 0.7,
            },
        )
        gen = CheckInGenerator()
        result = gen.generate(beliefs, week_data={})

        assert result["parameter"] == "deep_work_tolerance"

    def test_skip_when_all_confident(self):
        """When every parameter has confidence >= 0.85, skip the check-in."""
        beliefs = _make_beliefs(default_confidence=0.85)
        gen = CheckInGenerator()
        result = gen.generate(beliefs, week_data={})

        assert result["skip"] is True
        assert "good read" in result["message"].lower()

    def test_generates_question_text(self):
        """Lowest-confidence parameter (chaos=0.25) produces a question string."""
        beliefs = _make_beliefs(
            confidences={BeliefParameter.CHAOS_TOLERANCE: 0.25},
        )
        gen = CheckInGenerator()
        result = gen.generate(beliefs, week_data={})

        assert isinstance(result["question"], str)
        assert len(result["question"]) > 0
        assert isinstance(result["options"], list)
        assert len(result["options"]) >= 2

    def test_returns_options(self):
        """Lowest-confidence parameter (peak=0.2) returns an options list."""
        beliefs = _make_beliefs(
            confidences={BeliefParameter.PEAK_ENERGY: 0.2},
        )
        gen = CheckInGenerator()
        result = gen.generate(beliefs, week_data={})

        assert isinstance(result["options"], list)
        assert len(result["options"]) >= 2
