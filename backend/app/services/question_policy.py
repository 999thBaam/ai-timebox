from __future__ import annotations
"""
Question Policy - VOI/COI computation and decision logic.

Core principle: Ask only when knowing the answer changes the decision.
"""
from dataclasses import dataclass

from app.models.intent import IntentHypothesis, Unknown, BlockingFactor
from app.models.human_state import HumanState
from app.models.safety_policy import SafetyPolicy


@dataclass
class Assumption:
    """An assumption made instead of asking."""
    parameter: str
    assumed_value: str
    confidence: float
    undo_safe: bool


@dataclass
class Question:
    """A question to ask the user."""
    parameter: str
    text: str
    options: list[tuple[str, str]]  # (value, label)
    context: str


@dataclass
class QuestionDecision:
    """Result of question policy evaluation."""
    should_ask: bool
    question: Question | None = None
    assumptions: list[Assumption] | None = None


def compute_voi(
    unknown: Unknown,
    hypothesis: IntentHypothesis,
    state: HumanState,
) -> float:
    """
    Compute Value of Information for an unknown.

    Higher = more valuable to ask.
    Returns 0.0-1.0.
    """
    voi = 0.0

    # Factor 1: Blocking Factor
    blocking_weights = {
        BlockingFactor.LOW: 0.1,
        BlockingFactor.MEDIUM: 0.3,
        BlockingFactor.CRITICAL: 0.7,
    }
    voi += blocking_weights[unknown.blocking_factor]

    # Factor 2: Decision Sensitivity
    if unknown.parameter == "duration":
        voi += 0.3  # Duration heavily affects scheduling
    elif unknown.parameter == "time_preference":
        from app.models.intent import TemporalFlexibility
        if hypothesis.temporal_flexibility == TemporalFlexibility.FIXED:
            voi += 0.5
        else:
            voi += 0.1
    elif unknown.parameter == "participants":
        from app.models.intent import SocialRisk
        if hypothesis.social_risk == SocialRisk.HIGH:
            voi += 0.4
        else:
            voi += 0.1

    # Factor 3: State Sensitivity
    if state.fragility > 0.6:
        voi += 0.2  # Fragile user = higher cost of wrong assumptions
    if state.chaos_tolerance < 0.3:
        voi += 0.15  # Low chaos tolerance = need more certainty

    # Factor 4: Fallback Quality
    if hypothesis.volatility.fallback_action:
        voi -= 0.2  # Good fallback = less need to ask
    from app.models.intent import SocialRisk
    if hypothesis.social_risk == SocialRisk.NONE:
        voi -= 0.15  # Low social risk = can assume + undo

    return min(1.0, max(0.0, voi))


def compute_coi(state: HumanState, recent_questions: int) -> float:
    """
    Compute Cost of Interruption.

    Higher = more costly to interrupt.
    Returns 0.0-1.0.
    """
    coi = 0.0

    # Base cost from cognitive load
    coi += state.cognitive_load * 0.3

    # Fragility amplifies interruption cost
    coi += state.fragility * 0.2

    # Recent questions increase cost (diminishing patience)
    question_fatigue = min(0.4, recent_questions * 0.1)
    coi += question_fatigue

    return min(1.0, coi)


def generate_question(unknown: Unknown, hypothesis: IntentHypothesis) -> Question:
    """Generate a user-friendly question for an unknown."""
    if unknown.parameter == "duration":
        return Question(
            parameter="duration",
            text="How long do you need for this?",
            options=[
                ("30", "30 min"),
                ("60", "1 hour"),
                ("120", "2 hours"),
                ("180", "3+ hours"),
            ],
            context=f"This helps me schedule your {hypothesis.goal} better.",
        )
    elif unknown.parameter == "time_preference":
        return Question(
            parameter="time_preference",
            text="When works better for you?",
            options=[
                ("morning", "Morning"),
                ("afternoon", "Afternoon"),
                ("evening", "Evening"),
                ("flexible", "Flexible"),
            ],
            context="I'll find the best slot based on your energy patterns.",
        )
    elif unknown.parameter == "participants":
        return Question(
            parameter="participants",
            text="Will anyone else be joining?",
            options=[
                ("solo", "Just me"),
                ("others", "With others"),
            ],
            context="This helps me avoid scheduling conflicts.",
        )
    else:
        # Generic fallback
        return Question(
            parameter=unknown.parameter,
            text=f"Can you clarify: {unknown.parameter}?",
            options=[],
            context="I need this information to proceed.",
        )


def infer_default(unknown: Unknown, hypothesis: IntentHypothesis) -> str:
    """Infer a reasonable default for an unknown."""
    from app.models.intent import ActivityNature

    if unknown.parameter == "duration":
        # Duration defaults based on activity type
        defaults = {
            ActivityNature.DEEP_WORK: "60",
            ActivityNature.SHALLOW_WORK: "30",
            ActivityNature.MEETING: "30",
            ActivityNature.BREAK: "15",
            ActivityNature.PERSONAL: "60",
            ActivityNature.ADMIN: "30",
        }
        return defaults.get(hypothesis.activity_nature, "30")
    elif unknown.parameter == "time_preference":
        return "flexible"
    else:
        return ""


def evaluate_question_policy(
    hypothesis: IntentHypothesis,
    state: HumanState,
    policies: list[SafetyPolicy],
    recent_questions: int = 0,
) -> QuestionDecision:
    """
    Main entry point: decide ask / defer / assume.

    Rules:
    1. VOI > COI → Ask
    2. Critical + Non-deferrable → Ask anyway
    3. Deferrable → Defer
    4. Low risk + has fallback → Assume + Undo
    """
    if not hypothesis.unknowns:
        return QuestionDecision(should_ask=False, assumptions=[])

    coi = compute_coi(state, recent_questions)
    assumptions: list[Assumption] = []

    # Sort unknowns by VOI (highest first)
    sorted_unknowns = sorted(
        hypothesis.unknowns,
        key=lambda u: -compute_voi(u, hypothesis, state),
    )

    for unknown in sorted_unknowns:
        voi = compute_voi(unknown, hypothesis, state)

        # Rule 1: VOI > COI → Ask
        if voi > coi + 0.1:  # Small margin to avoid borderline asks
            return QuestionDecision(
                should_ask=True,
                question=generate_question(unknown, hypothesis),
            )

        # Rule 2: Critical + Non-deferrable → Ask anyway
        if unknown.blocking_factor == BlockingFactor.CRITICAL and not unknown.deferrable:
            return QuestionDecision(
                should_ask=True,
                question=generate_question(unknown, hypothesis),
            )

        # Rule 3: Deferrable → Skip (defer)
        if unknown.deferrable:
            continue

        # Rule 4: Low risk → Assume + Undo
        from app.models.intent import SocialRisk
        if (hypothesis.social_risk in [SocialRisk.NONE, SocialRisk.LOW] and
            hypothesis.volatility.fallback_action):
            assumptions.append(Assumption(
                parameter=unknown.parameter,
                assumed_value=infer_default(unknown, hypothesis),
                confidence=0.7,
                undo_safe=True,
            ))

    return QuestionDecision(
        should_ask=False,
        assumptions=assumptions if assumptions else None,
    )
