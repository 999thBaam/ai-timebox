"""Tests for AdaptiveQuestionnaire — conflict-aware onboarding with follow-ups."""
from __future__ import annotations

import pytest

from app.models.role_profile import BeliefParameter, RoleType
from app.services.adaptive_questionnaire import AdaptiveQuestionnaire


# ---------------------------------------------------------------------------
# Test: initialisation
# ---------------------------------------------------------------------------

class TestInit:
    def test_init_with_role(self):
        """AdaptiveQuestionnaire(STUDENT) has 3 pending questions."""
        aq = AdaptiveQuestionnaire(RoleType.STUDENT)
        assert len(aq.pending_questions) == 3


# ---------------------------------------------------------------------------
# Test: first question
# ---------------------------------------------------------------------------

class TestGetFirstQuestion:
    def test_get_first_question(self):
        """First question is energy_peak with 4 options."""
        aq = AdaptiveQuestionnaire(RoleType.STUDENT)
        q = aq.get_next_question()
        assert q is not None
        assert q["id"] == "energy_peak"
        assert "text" in q
        assert len(q["options"]) == 4


# ---------------------------------------------------------------------------
# Test: answer without conflict
# ---------------------------------------------------------------------------

class TestAnswerNoConflict:
    def test_answer_no_conflict(self):
        """Student default peak_energy=22.0 (Late Night). Answering 'Late Night' → no conflict."""
        aq = AdaptiveQuestionnaire(RoleType.STUDENT)
        result = aq.submit_answer("energy_peak", "Late Night")
        assert result["conflict"] is False


# ---------------------------------------------------------------------------
# Test: answer with conflict triggers follow-up
# ---------------------------------------------------------------------------

class TestAnswerWithConflict:
    def test_answer_with_conflict(self):
        """Student default peak_energy=22.0. Answering 'Morning' (9.0) → conflict, follow-up added."""
        aq = AdaptiveQuestionnaire(RoleType.STUDENT)
        result = aq.submit_answer("energy_peak", "Morning")
        assert result["conflict"] is True
        # A follow-up question should have been inserted
        assert len(aq.pending_questions) > 2  # was 2 remaining, now > 2


# ---------------------------------------------------------------------------
# Test: full flow min questions
# ---------------------------------------------------------------------------

class TestFullFlowMinQuestions:
    def test_full_flow_min_questions(self):
        """All matching answers → exactly 3 core questions, then None."""
        aq = AdaptiveQuestionnaire(RoleType.STUDENT)

        # Answer all three core questions with role-matching answers
        aq.get_next_question()  # energy_peak
        aq.submit_answer("energy_peak", "Late Night")

        aq.get_next_question()  # focus_duration
        aq.submit_answer("focus_duration", "30-60 min")

        aq.get_next_question()  # drain_source
        aq.submit_answer("drain_source", "Context switching")

        # No more questions
        assert aq.get_next_question() is None


# ---------------------------------------------------------------------------
# Test: get_beliefs
# ---------------------------------------------------------------------------

class TestGetBeliefs:
    def test_get_beliefs(self):
        """After answering Morning + 30-60min + Meetings → peak_energy=9.0, meeting_tolerance < 0.3."""
        aq = AdaptiveQuestionnaire(RoleType.STUDENT)

        aq.submit_answer("energy_peak", "Morning")
        aq.submit_answer("focus_duration", "30-60 min")
        aq.submit_answer("drain_source", "Meetings")

        beliefs = aq.get_beliefs()

        assert BeliefParameter.PEAK_ENERGY in beliefs
        assert beliefs[BeliefParameter.PEAK_ENERGY].belief_value == 9.0
        assert beliefs[BeliefParameter.PEAK_ENERGY].confidence == 0.5

        assert BeliefParameter.MEETING_TOLERANCE in beliefs
        assert beliefs[BeliefParameter.MEETING_TOLERANCE].belief_value < 0.3


# ---------------------------------------------------------------------------
# Test: get_summary
# ---------------------------------------------------------------------------

class TestGetSummary:
    def test_get_summary(self):
        """Summary returns a non-empty string > 20 chars."""
        aq = AdaptiveQuestionnaire(RoleType.STUDENT)

        aq.submit_answer("energy_peak", "Late Night")
        aq.submit_answer("focus_duration", "30-60 min")
        aq.submit_answer("drain_source", "Context switching")

        summary = aq.get_summary()
        assert isinstance(summary, str)
        assert len(summary) > 20
