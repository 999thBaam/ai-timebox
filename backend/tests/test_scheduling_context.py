from __future__ import annotations
"""Tests for SchedulingContext model and resolve_beliefs function."""

from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief
from app.models.scheduling_context import SchedulingContext, resolve_beliefs


def _make_beliefs(**overrides) -> dict[BeliefParameter, UserBelief]:
    defaults = {
        BeliefParameter.PEAK_ENERGY: 22.0,
        BeliefParameter.DEEP_WORK_TOLERANCE: 45.0,
        BeliefParameter.CONTEXT_SWITCH_COST: 0.7,
        BeliefParameter.CHAOS_TOLERANCE: 0.4,
        BeliefParameter.MEETING_TOLERANCE: 0.3,
        BeliefParameter.RECOVERY_RATE: 0.15,
        BeliefParameter.GUIDANCE_LEVEL: 0.5,
    }
    defaults.update(overrides)
    return {
        param: UserBelief(parameter=param, belief_value=val)
        for param, val in defaults.items()
    }


def test_resolve_peak_energy_window():
    ctx = resolve_beliefs(_make_beliefs())
    assert abs(ctx.peak_energy_start - 20.5) < 0.01
    assert abs(ctx.peak_energy_end - 23.5) < 0.01


def test_resolve_max_block_duration():
    ctx = resolve_beliefs(_make_beliefs())
    assert ctx.max_block_duration_minutes == 45.0


def test_resolve_buffer_from_context_switch_cost():
    ctx = resolve_beliefs(_make_beliefs())
    # 0.7 * 30 = 21.0
    assert abs(ctx.min_buffer_minutes - 21.0) < 0.01


def test_resolve_max_consecutive_meetings():
    ctx = resolve_beliefs(_make_beliefs())
    # round(0.3 * 5) = 2
    assert ctx.max_consecutive_meetings == 2


def test_resolve_manager_meetings():
    beliefs = _make_beliefs(**{BeliefParameter.MEETING_TOLERANCE: 0.8})
    ctx = resolve_beliefs(beliefs)
    # round(0.8 * 5) = 4
    assert ctx.max_consecutive_meetings == 4


def test_resolve_chaos_tolerance():
    ctx = resolve_beliefs(_make_beliefs())
    assert ctx.initial_chaos_tolerance == 0.4


def test_resolve_recovery_rate():
    ctx = resolve_beliefs(_make_beliefs())
    assert ctx.cognitive_recovery_rate == 0.15
