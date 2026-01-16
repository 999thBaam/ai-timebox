"""
Questionnaire Service - Onboarding and initial state calibration.

Purpose: Ask minimal high-value questions to calibrate initial state
without overwhelming the user.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from app.models.human_state import HumanState
from app.models.safety_policy import SafetyPolicy, ActivationCondition, PolicySource, DecayCurve


# ═══════════════════════════════════════════════════════════════════════════════
# QUESTIONNAIRE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

class QuestionCategory(str, Enum):
    ENERGY_PATTERNS = "energy_patterns"
    WORK_STYLE = "work_style"
    STRESS_TOLERANCE = "stress_tolerance"
    CALENDAR_PREFERENCES = "calendar_preferences"


@dataclass
class QuestionOption:
    value: str
    label: str
    impact: dict  # Maps to state adjustments


@dataclass
class OnboardingQuestion:
    id: str
    category: QuestionCategory
    question: str
    context: str
    options: list[QuestionOption]
    required: bool = True


# The minimal set of high-value questions
ONBOARDING_QUESTIONS: list[OnboardingQuestion] = [
    OnboardingQuestion(
        id="energy_peak",
        category=QuestionCategory.ENERGY_PATTERNS,
        question="When do you typically feel most focused and energetic?",
        context="This helps us schedule demanding tasks when you're at your best.",
        options=[
            QuestionOption("morning", "Morning (before noon)", 
                          {"peak_hours": [8, 12], "energy_modifier": 0.1}),
            QuestionOption("midday", "Midday (noon to 3pm)", 
                          {"peak_hours": [12, 15], "energy_modifier": 0.0}),
            QuestionOption("afternoon", "Late afternoon (3pm to 6pm)", 
                          {"peak_hours": [15, 18], "energy_modifier": -0.05}),
            QuestionOption("evening", "Evening (after 6pm)", 
                          {"peak_hours": [18, 22], "energy_modifier": -0.1}),
        ],
    ),
    OnboardingQuestion(
        id="deep_work_tolerance",
        category=QuestionCategory.WORK_STYLE,
        question="How long can you typically focus on demanding tasks before needing a break?",
        context="This helps us set appropriate session lengths and buffers.",
        options=[
            QuestionOption("short", "30-45 minutes", 
                          {"max_deep_work_minutes": 45, "fragility_modifier": 0.15}),
            QuestionOption("medium", "45-90 minutes", 
                          {"max_deep_work_minutes": 90, "fragility_modifier": 0.0}),
            QuestionOption("long", "90+ minutes", 
                          {"max_deep_work_minutes": 120, "fragility_modifier": -0.1}),
        ],
    ),
    OnboardingQuestion(
        id="transition_sensitivity",
        category=QuestionCategory.WORK_STYLE,
        question="How do you feel about back-to-back meetings or tasks?",
        context="This helps us add appropriate buffers between activities.",
        options=[
            QuestionOption("sensitive", "I need time to decompress between tasks", 
                          {"min_buffer_minutes": 15, "context_residue_modifier": 0.1}),
            QuestionOption("neutral", "Depends on the tasks", 
                          {"min_buffer_minutes": 10, "context_residue_modifier": 0.0}),
            QuestionOption("comfortable", "I can switch quickly", 
                          {"min_buffer_minutes": 5, "context_residue_modifier": -0.1}),
        ],
    ),
    OnboardingQuestion(
        id="chaos_response",
        category=QuestionCategory.STRESS_TOLERANCE,
        question="When your day gets disrupted, how do you typically react?",
        context="This helps us understand how to handle schedule changes.",
        options=[
            QuestionOption("stressed", "It throws me off significantly", 
                          {"chaos_tolerance": 0.3, "fragility": 0.6}),
            QuestionOption("adaptable", "I can adapt but it takes energy", 
                          {"chaos_tolerance": 0.5, "fragility": 0.4}),
            QuestionOption("flexible", "I roll with it easily", 
                          {"chaos_tolerance": 0.7, "fragility": 0.2}),
        ],
    ),
    OnboardingQuestion(
        id="notification_preference",
        category=QuestionCategory.CALENDAR_PREFERENCES,
        question="How much guidance do you want from your calendar?",
        context="This helps us decide when to ask questions vs. make decisions.",
        options=[
            QuestionOption("minimal", "Just schedule things, I trust the system", 
                          {"question_threshold": 0.7, "auto_decide": True}),
            QuestionOption("balanced", "Ask me about important decisions", 
                          {"question_threshold": 0.5, "auto_decide": False}),
            QuestionOption("involved", "I want to be consulted on most changes", 
                          {"question_threshold": 0.3, "auto_decide": False}),
        ],
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# CALIBRATION LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OnboardingAnswers:
    energy_peak: str
    deep_work_tolerance: str
    transition_sensitivity: str
    chaos_response: str
    notification_preference: str


def calibrate_initial_state(user_id: UUID, answers: OnboardingAnswers) -> HumanState:
    """
    Create initial HumanState based on questionnaire answers.
    """
    # Start with neutral baseline
    state = HumanState(
        user_id=user_id,
        updated_at=datetime.now(),
        cognitive_load=0.3,
        emotional_load=0.2,
        energy_level=0.7,
        context_residue=0.0,
        confidence=0.5,
        fragility=0.3,
        chaos_tolerance=0.5,
    )

    # Apply energy peak modifier
    energy_modifiers = {
        "morning": 0.1,
        "midday": 0.0,
        "afternoon": -0.05,
        "evening": -0.1,
    }
    state.energy_level += energy_modifiers.get(answers.energy_peak, 0.0)

    # Apply fragility from deep work tolerance
    fragility_modifiers = {
        "short": 0.15,
        "medium": 0.0,
        "long": -0.1,
    }
    state.fragility += fragility_modifiers.get(answers.deep_work_tolerance, 0.0)

    # Apply context residue from transition sensitivity
    residue_modifiers = {
        "sensitive": 0.1,
        "neutral": 0.0,
        "comfortable": -0.1,
    }
    state.context_residue = max(0.0, residue_modifiers.get(answers.transition_sensitivity, 0.0))

    # Apply chaos response
    chaos_settings = {
        "stressed": (0.3, 0.6),
        "adaptable": (0.5, 0.4),
        "flexible": (0.7, 0.2),
    }
    if answers.chaos_response in chaos_settings:
        state.chaos_tolerance, state.fragility = chaos_settings[answers.chaos_response]

    # Clamp all values
    state.energy_level = max(0.1, min(1.0, state.energy_level))
    state.fragility = max(0.0, min(1.0, state.fragility))
    state.chaos_tolerance = max(0.0, min(1.0, state.chaos_tolerance))

    return state


def create_default_policies(user_id: UUID, answers: OnboardingAnswers) -> list[SafetyPolicy]:
    """
    Create default safety policies based on questionnaire answers.
    """
    policies: list[SafetyPolicy] = []

    # Cognitive overload protection
    policies.append(SafetyPolicy(
        user_id=user_id,
        name="Prevent Cognitive Overload",
        source=PolicySource.QUESTIONNAIRE,
        protected_dimension="cognitive_load",
        activation_condition=ActivationCondition(
            metric="cognitive_load",
            operator=">",
            threshold=0.8,
        ),
        action={"type": "INSERT_BUFFER", "minutes": 15},
        initial_strength=1.0,
        current_strength=1.0,
        decay_curve=DecayCurve.EXPONENTIAL,
        decay_rate=0.02,
    ))

    # Energy protection
    policies.append(SafetyPolicy(
        user_id=user_id,
        name="Protect Low Energy",
        source=PolicySource.QUESTIONNAIRE,
        protected_dimension="confidence",
        activation_condition=ActivationCondition(
            metric="energy_level",
            operator="<",
            threshold=0.25,
        ),
        action={"type": "BLOCK_DEEP_WORK"},
        initial_strength=1.0,
        current_strength=1.0,
        decay_curve=DecayCurve.LINEAR,
        decay_rate=0.01,
    ))

    # Transition buffer based on sensitivity
    buffer_minutes = {
        "sensitive": 15,
        "neutral": 10,
        "comfortable": 5,
    }.get(answers.transition_sensitivity, 10)

    policies.append(SafetyPolicy(
        user_id=user_id,
        name="Transition Buffer",
        source=PolicySource.QUESTIONNAIRE,
        protected_dimension="cognitive_load",
        activation_condition=ActivationCondition(
            metric="context_residue",
            operator=">",
            threshold=0.3,
        ),
        action={"type": "INSERT_BUFFER", "minutes": buffer_minutes},
        initial_strength=0.8,
        current_strength=0.8,
        decay_curve=DecayCurve.EXPONENTIAL,
        decay_rate=0.03,
    ))

    # Fragility protection for those who are sensitive to disruption
    if answers.chaos_response == "stressed":
        policies.append(SafetyPolicy(
            user_id=user_id,
            name="Fragility Shield",
            source=PolicySource.QUESTIONNAIRE,
            protected_dimension="fragility",
            activation_condition=ActivationCondition(
                metric="fragility",
                operator=">",
                threshold=0.5,
            ),
            action={"type": "LIMIT_VISIBLE_TASKS", "max": 3},
            initial_strength=0.9,
            current_strength=0.9,
            decay_curve=DecayCurve.EXPONENTIAL,
            decay_rate=0.025,
        ))

    return policies


# ═══════════════════════════════════════════════════════════════════════════════
# API HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_onboarding_questions() -> list[dict]:
    """Get questionnaire for API response."""
    return [
        {
            "id": q.id,
            "category": q.category.value,
            "question": q.question,
            "context": q.context,
            "options": [{"value": o.value, "label": o.label} for o in q.options],
            "required": q.required,
        }
        for q in ONBOARDING_QUESTIONS
    ]


def process_onboarding(user_id: UUID, answers: dict) -> tuple[HumanState, list[SafetyPolicy]]:
    """
    Process onboarding answers and return calibrated state + policies.
    """
    onboarding_answers = OnboardingAnswers(
        energy_peak=answers.get("energy_peak", "midday"),
        deep_work_tolerance=answers.get("deep_work_tolerance", "medium"),
        transition_sensitivity=answers.get("transition_sensitivity", "neutral"),
        chaos_response=answers.get("chaos_response", "adaptable"),
        notification_preference=answers.get("notification_preference", "balanced"),
    )

    state = calibrate_initial_state(user_id, onboarding_answers)
    policies = create_default_policies(user_id, onboarding_answers)

    return state, policies
