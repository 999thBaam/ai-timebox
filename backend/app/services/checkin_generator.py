"""CheckInGenerator — weekly check-in service that targets the lowest-confidence belief."""

from __future__ import annotations

from typing import Any, Dict, List

from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONFIDENCE_SKIP_THRESHOLD: float = 0.8

# ---------------------------------------------------------------------------
# Question templates — one per BeliefParameter
# ---------------------------------------------------------------------------
QUESTION_TEMPLATES: Dict[BeliefParameter, Dict[str, Any]] = {
    BeliefParameter.PEAK_ENERGY: {
        "question": "When did you feel most productive this week?",
        "options": ["Morning", "Afternoon", "Evening", "Late Night"],
        "encoding": {
            "Morning": 9.0,
            "Afternoon": 14.0,
            "Evening": 20.0,
            "Late Night": 23.0,
        },
    },
    BeliefParameter.DEEP_WORK_TOLERANCE: {
        "question": "How did your focus block lengths feel?",
        "options": ["Too short", "About right", "Too long"],
        "encoding": {
            "Too short": 1.3,
            "About right": 1.0,
            "Too long": 0.7,
        },
    },
    BeliefParameter.CONTEXT_SWITCH_COST: {
        "question": "How did back-to-back switches feel?",
        "options": ["Exhausting", "Manageable", "No problem"],
        "encoding": {
            "Exhausting": 0.9,
            "Manageable": 0.5,
            "No problem": 0.2,
        },
    },
    BeliefParameter.CHAOS_TOLERANCE: {
        "question": "When schedule got disrupted, how did it feel?",
        "options": ["Threw me off", "Mildly annoying", "Didn't bother me"],
        "encoding": {
            "Threw me off": 0.2,
            "Mildly annoying": 0.5,
            "Didn't bother me": 0.8,
        },
    },
    BeliefParameter.MEETING_TOLERANCE: {
        "question": "How did your meeting load feel?",
        "options": ["Too many", "About right", "Could handle more"],
        "encoding": {
            "Too many": 0.2,
            "About right": 0.5,
            "Could handle more": 0.8,
        },
    },
    BeliefParameter.RECOVERY_RATE: {
        "question": "After focus blocks, were breaks long enough?",
        "options": ["Needed more", "Just right", "Shorter"],
        "encoding": {
            "Needed more": 0.05,
            "Just right": 0.10,
            "Shorter": 0.18,
        },
    },
    BeliefParameter.GUIDANCE_LEVEL: {
        "question": "How did prompts and suggestions feel?",
        "options": ["Too many", "Just right", "Want more"],
        "encoding": {
            "Too many": 0.2,
            "Just right": 0.5,
            "Want more": 0.8,
        },
    },
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class CheckInGenerator:
    """Generates a weekly check-in question targeting the belief with the lowest confidence."""

    def generate(
        self,
        beliefs: Dict[BeliefParameter, UserBelief],
        week_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Produce a check-in payload.

        If every belief's confidence exceeds CONFIDENCE_SKIP_THRESHOLD the
        check-in is skipped.  Otherwise the parameter with the lowest
        confidence is selected and the corresponding question template is
        returned.

        Args:
            beliefs: Mapping of BeliefParameter -> UserBelief for the user.
            week_data: Summary data for the past week (reserved for future use).

        Returns:
            A dict with either:
                - {"skip": True, "message": "..."} when all beliefs are confident
                - {"parameter": str, "question": str, "options": list, "encoding": dict}
        """
        # Check whether all beliefs are confident enough to skip
        if all(b.confidence > CONFIDENCE_SKIP_THRESHOLD for b in beliefs.values()):
            return {
                "skip": True,
                "message": "We have a good read on your preferences — no check-in needed this week.",
            }

        # Find the parameter with the lowest confidence
        lowest_param = min(beliefs, key=lambda p: beliefs[p].confidence)
        template = QUESTION_TEMPLATES[lowest_param]

        return {
            "parameter": lowest_param.value,
            "question": template["question"],
            "options": list(template["options"]),
            "encoding": dict(template["encoding"]),
        }
