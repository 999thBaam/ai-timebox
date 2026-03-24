from __future__ import annotations
"""Role Profile Model - Role-based personality classification with belief parameter defaults."""
from dataclasses import dataclass, field
from enum import Enum


class BeliefParameter(str, Enum):
    """The 7 core belief parameters that define scheduling personality."""
    PEAK_ENERGY = "peak_energy"
    DEEP_WORK_TOLERANCE = "deep_work_tolerance"
    CONTEXT_SWITCH_COST = "context_switch_cost"
    CHAOS_TOLERANCE = "chaos_tolerance"
    MEETING_TOLERANCE = "meeting_tolerance"
    RECOVERY_RATE = "recovery_rate"
    GUIDANCE_LEVEL = "guidance_level"


class RoleType(str, Enum):
    """The 5 supported role archetypes."""
    STUDENT = "student"
    PROFESSIONAL = "professional"
    FREELANCER = "freelancer"
    MANAGER = "manager"
    CREATIVE = "creative"


@dataclass(frozen=True)
class RoleProfile:
    """
    A frozen profile containing role-specific defaults for belief parameters
    and default safety policies.

    Role profiles provide sensible starting points for each archetype.
    These defaults are refined over time via behavioral observation.
    """
    role: RoleType
    defaults: dict[BeliefParameter, float] = field(default_factory=dict)
    default_policies: list[dict[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Role profile definitions
# ---------------------------------------------------------------------------

_STUDENT_PROFILE = RoleProfile(
    role=RoleType.STUDENT,
    defaults={
        BeliefParameter.PEAK_ENERGY: 22.0,
        BeliefParameter.DEEP_WORK_TOLERANCE: 45.0,
        BeliefParameter.MEETING_TOLERANCE: 0.3,
        BeliefParameter.CONTEXT_SWITCH_COST: 0.7,
        BeliefParameter.CHAOS_TOLERANCE: 0.4,
        BeliefParameter.RECOVERY_RATE: 0.15,
        BeliefParameter.GUIDANCE_LEVEL: 0.5,
    },
    default_policies=[
        {
            "description": "Block scheduling after 2am to protect sleep",
            "condition": "time_of_day > 2:00 AND time_of_day < 6:00",
            "action": "BLOCK_SCHEDULING",
        },
        {
            "description": "Insert break after 45 min deep work session",
            "condition": "continuous_focus_minutes >= 45",
            "action": "INSERT_BREAK_15",
        },
    ],
)

_PROFESSIONAL_PROFILE = RoleProfile(
    role=RoleType.PROFESSIONAL,
    defaults={
        BeliefParameter.PEAK_ENERGY: 10.5,
        BeliefParameter.DEEP_WORK_TOLERANCE: 90.0,
        BeliefParameter.MEETING_TOLERANCE: 0.6,
        BeliefParameter.CONTEXT_SWITCH_COST: 0.5,
        BeliefParameter.CHAOS_TOLERANCE: 0.5,
        BeliefParameter.RECOVERY_RATE: 0.10,
        BeliefParameter.GUIDANCE_LEVEL: 0.3,
    },
    default_policies=[
        {
            "description": "Protect morning deep-work block from meetings",
            "condition": "time_of_day >= 9:00 AND time_of_day < 11:00 AND event_type == meeting",
            "action": "WARN_DEEP_WORK_CONFLICT",
        },
        {
            "description": "Limit back-to-back meetings to 3 consecutive",
            "condition": "consecutive_meetings >= 3",
            "action": "INSERT_BUFFER_15",
        },
    ],
)

_FREELANCER_PROFILE = RoleProfile(
    role=RoleType.FREELANCER,
    defaults={
        BeliefParameter.PEAK_ENERGY: 11.5,
        BeliefParameter.DEEP_WORK_TOLERANCE: 60.0,
        BeliefParameter.MEETING_TOLERANCE: 0.4,
        BeliefParameter.CONTEXT_SWITCH_COST: 0.6,
        BeliefParameter.CHAOS_TOLERANCE: 0.6,
        BeliefParameter.RECOVERY_RATE: 0.12,
        BeliefParameter.GUIDANCE_LEVEL: 0.4,
    },
    default_policies=[
        {
            "description": "Warn when task count exceeds sustainable daily limit",
            "condition": "daily_task_count > 8",
            "action": "WARN_OVERCOMMIT",
        },
        {
            "description": "Protect late evening from client work",
            "condition": "time_of_day > 21:00 AND task_type == client_work",
            "action": "SUGGEST_DEFER",
        },
    ],
)

_MANAGER_PROFILE = RoleProfile(
    role=RoleType.MANAGER,
    defaults={
        BeliefParameter.PEAK_ENERGY: 9.5,
        BeliefParameter.DEEP_WORK_TOLERANCE: 30.0,
        BeliefParameter.MEETING_TOLERANCE: 0.8,
        BeliefParameter.CONTEXT_SWITCH_COST: 0.3,
        BeliefParameter.CHAOS_TOLERANCE: 0.7,
        BeliefParameter.RECOVERY_RATE: 0.08,
        BeliefParameter.GUIDANCE_LEVEL: 0.2,
    },
    default_policies=[
        {
            "description": "Reserve one 30-min deep-work slot daily",
            "condition": "daily_deep_work_minutes < 30",
            "action": "RESERVE_DEEP_WORK_SLOT",
        },
        {
            "description": "Insert decompression buffer after 4+ hours of meetings",
            "condition": "cumulative_meeting_hours >= 4",
            "action": "INSERT_BUFFER_30",
        },
    ],
)

_CREATIVE_PROFILE = RoleProfile(
    role=RoleType.CREATIVE,
    defaults={
        BeliefParameter.PEAK_ENERGY: 23.5,
        BeliefParameter.DEEP_WORK_TOLERANCE: 120.0,
        BeliefParameter.MEETING_TOLERANCE: 0.2,
        BeliefParameter.CONTEXT_SWITCH_COST: 0.8,
        BeliefParameter.CHAOS_TOLERANCE: 0.5,
        BeliefParameter.RECOVERY_RATE: 0.07,
        BeliefParameter.GUIDANCE_LEVEL: 0.6,
    },
    default_policies=[
        {
            "description": "Block all meetings during peak creative hours",
            "condition": "time_of_day >= 22:00 OR time_of_day < 3:00 AND event_type == meeting",
            "action": "BLOCK_MEETING",
        },
        {
            "description": "Prevent context switches during flow state",
            "condition": "flow_state == active AND minutes_in_flow < 90",
            "action": "DEFER_INTERRUPTIONS",
        },
    ],
)

_ROLE_PROFILES: dict[RoleType, RoleProfile] = {
    RoleType.STUDENT: _STUDENT_PROFILE,
    RoleType.PROFESSIONAL: _PROFESSIONAL_PROFILE,
    RoleType.FREELANCER: _FREELANCER_PROFILE,
    RoleType.MANAGER: _MANAGER_PROFILE,
    RoleType.CREATIVE: _CREATIVE_PROFILE,
}


def get_role_profile(role: RoleType) -> RoleProfile:
    """
    Get the default role profile for a given role type.

    Args:
        role: The RoleType to look up.

    Returns:
        A frozen RoleProfile with sensible defaults for the role.

    Raises:
        KeyError: If the role type is not recognized.
    """
    return _ROLE_PROFILES[role]
