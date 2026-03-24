from __future__ import annotations
"""SchedulingContext Model - Resolves user beliefs into concrete scheduling parameters."""

from dataclasses import dataclass

from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief


@dataclass(frozen=True)
class SchedulingContext:
    """
    Concrete scheduling parameters derived from a user's belief system.

    This frozen dataclass is the bridge between the probabilistic belief
    model and the deterministic planner. The `resolve_beliefs` function
    converts raw beliefs into actionable scheduling constraints.
    """

    peak_energy_start: float
    peak_energy_end: float
    max_block_duration_minutes: float
    min_buffer_minutes: float
    initial_chaos_tolerance: float
    max_consecutive_meetings: int
    cognitive_recovery_rate: float
    guidance_level: float = 0.5


def resolve_beliefs(beliefs: dict[BeliefParameter, UserBelief]) -> SchedulingContext:
    """
    Convert a dict of UserBeliefs into a concrete SchedulingContext.

    Each belief's value is transformed into an actionable scheduling
    parameter:
    - peak_energy: 3-hour window centered on the belief value
    - deep_work_tolerance: direct map to max block duration in minutes
    - context_switch_cost: multiplied by 30 to get buffer minutes
    - chaos_tolerance: direct map
    - meeting_tolerance: multiplied by 5 and rounded for max consecutive meetings
    - recovery_rate: direct map
    - guidance_level: direct map

    Args:
        beliefs: Mapping of BeliefParameter to UserBelief for all 7 parameters.

    Returns:
        A frozen SchedulingContext ready for the planner.
    """
    peak = beliefs[BeliefParameter.PEAK_ENERGY].belief_value
    return SchedulingContext(
        peak_energy_start=peak - 1.5,
        peak_energy_end=peak + 1.5,
        max_block_duration_minutes=beliefs[BeliefParameter.DEEP_WORK_TOLERANCE].belief_value,
        min_buffer_minutes=beliefs[BeliefParameter.CONTEXT_SWITCH_COST].belief_value * 30,
        initial_chaos_tolerance=beliefs[BeliefParameter.CHAOS_TOLERANCE].belief_value,
        max_consecutive_meetings=round(beliefs[BeliefParameter.MEETING_TOLERANCE].belief_value * 5),
        cognitive_recovery_rate=beliefs[BeliefParameter.RECOVERY_RATE].belief_value,
        guidance_level=beliefs[BeliefParameter.GUIDANCE_LEVEL].belief_value,
    )
