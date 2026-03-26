"""
Adaptive Questionnaire Service — Conflict-aware onboarding with follow-up questions.

Purpose: Ask 3 core questions calibrated to the user's chosen role, detect
conflicts between their answers and role defaults, and inject targeted
follow-up questions when conflicts exceed a threshold.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Optional

from app.models.role_profile import BeliefParameter, RoleType, get_role_profile, RoleProfile
from app.models.user_belief import UserBelief


# ---------------------------------------------------------------------------
# Encodings  (human-readable answer → numeric belief value)
# ---------------------------------------------------------------------------

ENERGY_ENCODING: dict[str, float] = {
    "Morning": 9.0,
    "Afternoon": 14.0,
    "Evening": 20.0,
    "Late Night": 23.0,
}

FOCUS_ENCODING: dict[str, float] = {
    "Under 30 min": 25.0,
    "30-60 min": 45.0,
    "1-2 hours": 90.0,
    "2+ hours": 150.0,
}

# ---------------------------------------------------------------------------
# Question definitions
# ---------------------------------------------------------------------------

_CORE_QUESTIONS: list[dict] = [
    {
        "id": "energy_peak",
        "text": "You have one important task to finish today. When would you schedule it?",
        "options": ["Morning", "Afternoon", "Evening", "Late Night"],
        "parameter": BeliefParameter.PEAK_ENERGY,
    },
    {
        "id": "focus_duration",
        "text": "You're solving a hard problem. How long before you'd want to step away?",
        "options": ["Under 30 min", "30-60 min", "1-2 hours", "2+ hours"],
        "parameter": BeliefParameter.DEEP_WORK_TOLERANCE,
    },
    {
        "id": "drain_source",
        "text": "Think about your worst workday recently. What made it exhausting?",
        "options": ["Too many calls and meetings", "Jumping between different tasks", "Staying focused for too long", "People and notifications breaking my flow"],
        "parameter": None,  # maps to multiple beliefs
    },
]

_FOLLOW_UP_TEMPLATES: dict[str, dict] = {
    "schedule_flexibility": {
        "id": "schedule_flexibility",
        "text": "An unexpected meeting lands on your calendar. What happens to the rest of your day?",
        "options": ["Very rigid", "Somewhat flexible", "Very flexible", "Completely open"],
        "parameter": BeliefParameter.CHAOS_TOLERANCE,
    },
    "work_pattern": {
        "id": "work_pattern",
        "text": "You have 4 free hours. Do you tackle one big thing or several small ones?",
        "options": ["Long blocks", "Medium blocks", "Short sprints", "Mixed"],
        "parameter": BeliefParameter.DEEP_WORK_TOLERANCE,
    },
    "disruption_response": {
        "id": "disruption_response",
        "text": "Your morning plan just fell apart. What do you actually do?",
        "options": ["Rework the plan", "Adjust and continue", "Push through anyway"],
        "parameter": BeliefParameter.CHAOS_TOLERANCE,
    },
    "meeting_limit": {
        "id": "meeting_limit",
        "text": "Imagine a day packed with back-to-back calls. How many before you'd cancel one?",
        "options": ["2 or fewer", "3-4", "5+", "No limit"],
        "parameter": BeliefParameter.MEETING_TOLERANCE,
    },
}

# Mapping: which follow-ups attach to which core question conflicts
_CONFLICT_FOLLOW_UPS: dict[str, str] = {
    "energy_peak": "schedule_flexibility",
    "focus_duration": "work_pattern",
    "drain_source": "meeting_limit",
}

CONFLICT_THRESHOLD: float = 0.3

# Parameter ranges used for normalisation
_PARAMETER_RANGES: dict[BeliefParameter, float] = {
    BeliefParameter.PEAK_ENERGY: 24.0,  # circular
    BeliefParameter.DEEP_WORK_TOLERANCE: 150.0,
    BeliefParameter.MEETING_TOLERANCE: 1.0,
    BeliefParameter.CONTEXT_SWITCH_COST: 1.0,
    BeliefParameter.CHAOS_TOLERANCE: 1.0,
    BeliefParameter.RECOVERY_RATE: 1.0,
    BeliefParameter.GUIDANCE_LEVEL: 1.0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _circular_distance(a: float, b: float, period: float = 24.0) -> float:
    """Shortest distance on a circular scale (e.g. hours of the day)."""
    diff = abs(a - b)
    return min(diff, period - diff)


def _compute_conflict(encoded_value: float, role_default: float, param: BeliefParameter) -> float:
    """Return normalised conflict score in [0, 1]."""
    p_range = _PARAMETER_RANGES.get(param, 1.0)
    if param == BeliefParameter.PEAK_ENERGY:
        return _circular_distance(encoded_value, role_default) / p_range
    return abs(encoded_value - role_default) / p_range


# ---------------------------------------------------------------------------
# Drain-source mappings
# ---------------------------------------------------------------------------

_DRAIN_ADJUSTMENTS: dict[str, tuple[BeliefParameter, float]] = {
    "Too many calls and meetings": (BeliefParameter.MEETING_TOLERANCE, -0.2),
    "Jumping between different tasks": (BeliefParameter.CONTEXT_SWITCH_COST, 0.2),
    "Staying focused for too long": (BeliefParameter.DEEP_WORK_TOLERANCE, -15.0),
}

# ---------------------------------------------------------------------------
# Follow-up answer mappings
# ---------------------------------------------------------------------------

_DISRUPTION_RESPONSE_MAP: dict[str, float] = {
    "Rework the plan": 0.3,
    "Adjust and continue": 0.5,
    "Push through anyway": 0.7,
}

_MEETING_LIMIT_MAP: dict[str, float] = {
    "2 or fewer": 0.2,
    "3-4": 0.5,
    "5+": 0.8,
    "No limit": 0.9,
}

_SCHEDULE_FLEXIBILITY_MAP: dict[str, float] = {
    "Very rigid": 0.2,
    "Somewhat flexible": 0.4,
    "Very flexible": 0.7,
    "Completely open": 0.9,
}

_WORK_PATTERN_MAP: dict[str, float] = {
    "Long blocks": 120.0,
    "Medium blocks": 75.0,
    "Short sprints": 30.0,
    "Mixed": 60.0,
}


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class AdaptiveQuestionnaire:
    """
    Stateful questionnaire that detects conflicts between user answers and
    role defaults, injecting follow-up questions when needed.
    """

    def __init__(self, role: RoleType) -> None:
        self.role = role
        self.profile: RoleProfile = get_role_profile(role)
        self.pending_questions: list[dict] = [deepcopy(q) for q in _CORE_QUESTIONS]
        self.answers: dict[str, str] = {}
        self._belief_adjustments: dict[BeliefParameter, float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_next_question(self) -> Optional[dict]:
        """Return the next pending question as a dict, or None if done."""
        if not self.pending_questions:
            return None
        q = self.pending_questions[0]
        return {"id": q["id"], "text": q["text"], "options": q["options"]}

    def submit_answer(self, question_id: str, answer: str) -> dict:
        """
        Record an answer, compute conflict, optionally insert follow-up.

        Returns {"conflict": bool}.
        """
        self.answers[question_id] = answer

        # Remove the answered question from pending
        self.pending_questions = [
            q for q in self.pending_questions if q["id"] != question_id
        ]

        conflict = False

        if question_id == "energy_peak":
            encoded = ENERGY_ENCODING.get(answer, 22.0)
            role_default = self.profile.defaults[BeliefParameter.PEAK_ENERGY]
            self._belief_adjustments[BeliefParameter.PEAK_ENERGY] = encoded
            score = _compute_conflict(encoded, role_default, BeliefParameter.PEAK_ENERGY)
            if score > CONFLICT_THRESHOLD:
                conflict = True

        elif question_id == "focus_duration":
            encoded = FOCUS_ENCODING.get(answer, 45.0)
            role_default = self.profile.defaults[BeliefParameter.DEEP_WORK_TOLERANCE]
            self._belief_adjustments[BeliefParameter.DEEP_WORK_TOLERANCE] = encoded
            score = _compute_conflict(encoded, role_default, BeliefParameter.DEEP_WORK_TOLERANCE)
            if score > CONFLICT_THRESHOLD:
                conflict = True

        elif question_id == "drain_source":
            if answer in _DRAIN_ADJUSTMENTS:
                param, delta = _DRAIN_ADJUSTMENTS[answer]
                base = self.profile.defaults.get(param, 0.5)
                self._belief_adjustments[param] = base + delta
            # drain_source can also conflict when "Meetings" is selected for a role
            # that expects high meeting tolerance
            if answer == "Too many calls and meetings":
                role_meeting = self.profile.defaults.get(BeliefParameter.MEETING_TOLERANCE, 0.5)
                if role_meeting > 0.5:
                    conflict = True

        elif question_id == "disruption_response":
            val = _DISRUPTION_RESPONSE_MAP.get(answer, 0.5)
            self._belief_adjustments[BeliefParameter.CHAOS_TOLERANCE] = val

        elif question_id == "meeting_limit":
            val = _MEETING_LIMIT_MAP.get(answer, 0.5)
            self._belief_adjustments[BeliefParameter.MEETING_TOLERANCE] = val

        elif question_id == "schedule_flexibility":
            val = _SCHEDULE_FLEXIBILITY_MAP.get(answer, 0.5)
            self._belief_adjustments[BeliefParameter.CHAOS_TOLERANCE] = val

        elif question_id == "work_pattern":
            val = _WORK_PATTERN_MAP.get(answer, 60.0)
            self._belief_adjustments[BeliefParameter.DEEP_WORK_TOLERANCE] = val

        # Insert follow-up if conflict detected
        if conflict and question_id in _CONFLICT_FOLLOW_UPS:
            follow_up_key = _CONFLICT_FOLLOW_UPS[question_id]
            follow_up = deepcopy(_FOLLOW_UP_TEMPLATES[follow_up_key])
            # Only insert if not already in pending
            existing_ids = {q["id"] for q in self.pending_questions}
            if follow_up["id"] not in existing_ids:
                self.pending_questions.insert(0, follow_up)

        return {"conflict": conflict}

    def get_beliefs(self) -> dict[BeliefParameter, UserBelief]:
        """
        Build a dict of UserBelief objects from role defaults + answer adjustments.

        All beliefs start with confidence=0.5.
        """
        beliefs: dict[BeliefParameter, UserBelief] = {}

        for param in BeliefParameter:
            role_default = self.profile.defaults.get(param, 0.5)
            value = self._belief_adjustments.get(param, role_default)
            beliefs[param] = UserBelief(
                parameter=param,
                belief_value=value,
                confidence=0.5,
            )

        return beliefs

    def get_policies(self) -> list[dict]:
        """
        Return safety policies derived from the role profile's default_policies,
        plus any adaptive policies based on questionnaire answers.

        Each policy is a dict with description/condition/action keys.
        """
        policies = list(self.profile.default_policies)

        # If context_switch_cost is high, add a buffer policy
        beliefs = self.get_beliefs()
        context_switch_cost = beliefs[BeliefParameter.CONTEXT_SWITCH_COST].belief_value
        if context_switch_cost > 0.6:
            policies.append({
                "description": "Insert buffer between tasks due to high context-switch cost",
                "condition": "task_transition == true",
                "action": "INSERT_BUFFER_10",
            })

        return policies

    def get_summary(self) -> str:
        """Return a natural-language summary of the user's profile based on answers."""
        beliefs = self.get_beliefs()

        energy_val = beliefs[BeliefParameter.PEAK_ENERGY].belief_value
        focus_val = beliefs[BeliefParameter.DEEP_WORK_TOLERANCE].belief_value
        meeting_val = beliefs[BeliefParameter.MEETING_TOLERANCE].belief_value

        # Determine time-of-day label
        if energy_val < 12:
            time_label = "morning"
        elif energy_val < 17:
            time_label = "afternoon"
        elif energy_val < 21:
            time_label = "evening"
        else:
            time_label = "late-night"

        # Determine focus label
        if focus_val <= 30:
            focus_label = "short"
        elif focus_val <= 60:
            focus_label = f"{int(focus_val)}-minute"
        elif focus_val <= 120:
            focus_label = f"{int(focus_val)}-minute deep"
        else:
            focus_label = "extended"

        # Meeting preference
        if meeting_val < 0.3:
            meeting_label = "minimal meetings"
        elif meeting_val < 0.6:
            meeting_label = "moderate meetings"
        else:
            meeting_label = "meeting-heavy days"

        return (
            f"You're set up for {time_label} deep work in {focus_label} sprints, "
            f"with a preference for {meeting_label}."
        )
