from __future__ import annotations
"""
Intent Hypothesis Engine - Build full IHF 2.0 from parsed LLM output.

Responsibilities:
1. Convert parsed intent to full IntentHypothesis
2. Identify unknowns and set blocking factors
3. Compute activity profiles and transition requirements
"""
from datetime import datetime, time

from app.models.intent import (
    IntentHypothesis,
    TransitionProfile,
    Volatility,
    Unknown,
    ActivityNature,
    EnergyLevel,
    TemporalFlexibility,
    SpatialFlexibility,
    SocialRisk,
    BlockingFactor,
)
from app.services.llm_provider import ParsedIntent


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSITION PROFILES BY ACTIVITY
# ═══════════════════════════════════════════════════════════════════════════════

TRANSITION_PROFILES: dict[ActivityNature, TransitionProfile] = {
    ActivityNature.DEEP_WORK: TransitionProfile(
        ramp_up_minutes=15,
        cool_down_minutes=10,
        context_residue=0.4,
    ),
    ActivityNature.SHALLOW_WORK: TransitionProfile(
        ramp_up_minutes=5,
        cool_down_minutes=5,
        context_residue=0.15,
    ),
    ActivityNature.MEETING: TransitionProfile(
        ramp_up_minutes=5,
        cool_down_minutes=10,
        context_residue=0.3,
    ),
    ActivityNature.BREAK: TransitionProfile(
        ramp_up_minutes=0,
        cool_down_minutes=0,
        context_residue=0.0,
    ),
    ActivityNature.PERSONAL: TransitionProfile(
        ramp_up_minutes=5,
        cool_down_minutes=5,
        context_residue=0.2,
    ),
    ActivityNature.ADMIN: TransitionProfile(
        ramp_up_minutes=5,
        cool_down_minutes=5,
        context_residue=0.1,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT DURATIONS BY ACTIVITY
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_DURATIONS: dict[ActivityNature, int] = {
    ActivityNature.DEEP_WORK: 90,
    ActivityNature.SHALLOW_WORK: 30,
    ActivityNature.MEETING: 30,
    ActivityNature.BREAK: 15,
    ActivityNature.PERSONAL: 60,
    ActivityNature.ADMIN: 30,
}


def build_hypothesis(parsed: ParsedIntent, raw_input: str) -> IntentHypothesis:
    """
    Build a full IntentHypothesis from parsed LLM output.
    
    Identifies unknowns, sets appropriate blocking factors,
    and fills in defaults where needed.
    """
    # Map activity nature
    try:
        activity_nature = ActivityNature(parsed.activity_nature)
    except ValueError:
        activity_nature = ActivityNature.SHALLOW_WORK

    # Map energy level
    try:
        energy_level = EnergyLevel(parsed.energy_level_required)
    except ValueError:
        energy_level = EnergyLevel.MEDIUM

    # Get transition profile
    transition = TRANSITION_PROFILES.get(
        activity_nature,
        TRANSITION_PROFILES[ActivityNature.SHALLOW_WORK]
    )

    # Identify unknowns
    unknowns: list[Unknown] = []

    # Duration
    if parsed.duration_minutes is None:
        unknowns.append(Unknown(
            parameter="duration",
            blocking_factor=BlockingFactor.MEDIUM,
            deferrable=True,  # Can use default
        ))
        duration = DEFAULT_DURATIONS.get(activity_nature, 30)
    else:
        duration = parsed.duration_minutes

    # Time preference
    preferred_window: tuple[time, time] | None = None
    temporal_flexibility = TemporalFlexibility.FLEXIBLE

    if parsed.time_preference:
        pref = parsed.time_preference.lower()
        if "morning" in pref:
            preferred_window = (time(8, 0), time(12, 0))
        elif "afternoon" in pref:
            preferred_window = (time(12, 0), time(17, 0))
        elif "evening" in pref:
            preferred_window = (time(17, 0), time(22, 0))
        elif "flexible" in pref or "anytime" in pref:
            temporal_flexibility = TemporalFlexibility.ANYTIME
    else:
        # Unknown time preference
        unknowns.append(Unknown(
            parameter="time_preference",
            blocking_factor=BlockingFactor.LOW,
            deferrable=True,
        ))

    # Participants and social risk
    participants = parsed.participants or []
    if participants:
        social_risk = SocialRisk.HIGH  # Coordination needed
    else:
        social_risk = SocialRisk.NONE

    # Volatility based on participants
    stability = 0.9 if not participants else 0.7
    fallback = None if participants else "reschedule"

    # Build hypothesis
    hypothesis = IntentHypothesis(
        created_at=datetime.now(),
        raw_input=raw_input,
        goal=parsed.goal,
        participants=participants,
        activity_nature=activity_nature,
        energy_level_required=energy_level,
        transition_profile=transition,
        temporal_flexibility=temporal_flexibility,
        preferred_window=preferred_window,
        duration_estimate_minutes=duration,
        spatial_flexibility=SpatialFlexibility.FLEXIBLE,
        social_risk=social_risk,
        volatility=Volatility(
            stability_score=stability,
            dependencies=[],
            fallback_action=fallback,
        ),
        unknowns=unknowns,
        confidence=parsed.confidence,
    )

    return hypothesis


def resolve_unknown(
    hypothesis: IntentHypothesis,
    parameter: str,
    value: str,
) -> IntentHypothesis:
    """
    Resolve an unknown in the hypothesis with a user-provided value.
    """
    from dataclasses import replace

    # Remove from unknowns
    new_unknowns = [u for u in hypothesis.unknowns if u.parameter != parameter]

    # Apply value
    updates: dict = {"unknowns": new_unknowns}

    if parameter == "duration":
        # Parse duration (e.g., "30 min", "1 hour", "2 hours")
        value_lower = value.lower()
        if "hour" in value_lower:
            num = int("".join(c for c in value if c.isdigit()) or "1")
            updates["duration_estimate_minutes"] = num * 60
        else:
            num = int("".join(c for c in value if c.isdigit()) or "30")
            updates["duration_estimate_minutes"] = num

    elif parameter == "time_preference":
        value_lower = value.lower()
        if "morning" in value_lower:
            updates["preferred_window"] = (time(8, 0), time(12, 0))
        elif "afternoon" in value_lower:
            updates["preferred_window"] = (time(12, 0), time(17, 0))
        elif "evening" in value_lower:
            updates["preferred_window"] = (time(17, 0), time(22, 0))
        else:
            updates["temporal_flexibility"] = TemporalFlexibility.ANYTIME

    return replace(hypothesis, **updates)
