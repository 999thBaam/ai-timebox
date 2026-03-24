"""Tests for BehavioralTracker — routes behavioral signals through BeliefUpdater."""

from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief
from app.services.behavioral_tracker import BehavioralTracker


def _make_beliefs() -> dict[BeliefParameter, UserBelief]:
    """Create all 7 beliefs with student-like defaults."""
    return {
        BeliefParameter.PEAK_ENERGY: UserBelief(
            parameter=BeliefParameter.PEAK_ENERGY, belief_value=22.0
        ),
        BeliefParameter.DEEP_WORK_TOLERANCE: UserBelief(
            parameter=BeliefParameter.DEEP_WORK_TOLERANCE, belief_value=45.0
        ),
        BeliefParameter.CONTEXT_SWITCH_COST: UserBelief(
            parameter=BeliefParameter.CONTEXT_SWITCH_COST, belief_value=0.7
        ),
        BeliefParameter.CHAOS_TOLERANCE: UserBelief(
            parameter=BeliefParameter.CHAOS_TOLERANCE, belief_value=0.4
        ),
        BeliefParameter.MEETING_TOLERANCE: UserBelief(
            parameter=BeliefParameter.MEETING_TOLERANCE, belief_value=0.3
        ),
        BeliefParameter.RECOVERY_RATE: UserBelief(
            parameter=BeliefParameter.RECOVERY_RATE, belief_value=0.15
        ),
        BeliefParameter.GUIDANCE_LEVEL: UserBelief(
            parameter=BeliefParameter.GUIDANCE_LEVEL, belief_value=0.5
        ),
    }


class TestBehavioralTracker:
    """BehavioralTracker delegates to BeliefUpdater correctly."""

    def test_track_block_completion(self) -> None:
        """Block at 14.0, 45min, completed -> peak_energy shifts (!=22.0)."""
        tracker = BehavioralTracker()
        beliefs = _make_beliefs()

        updated = tracker.on_block_status_change(
            beliefs=beliefs,
            block_start_hour=14.0,
            block_duration_minutes=45,
            new_status="completed",
        )

        peak = updated[BeliefParameter.PEAK_ENERGY].belief_value
        assert peak != 22.0, f"peak_energy should have shifted from 22.0, got {peak}"

    def test_track_reschedule(self) -> None:
        """Reschedule from 22.0 to 15.0 -> peak < 22.0."""
        tracker = BehavioralTracker()
        beliefs = _make_beliefs()

        updated = tracker.on_reschedule(
            beliefs=beliefs,
            original_hour=22.0,
            new_hour=15.0,
        )

        peak = updated[BeliefParameter.PEAK_ENERGY].belief_value
        assert peak < 22.0, f"peak_energy should be < 22.0 after reschedule, got {peak}"

    def test_track_self_schedule(self) -> None:
        """Self-scheduled at 10.0, 60min -> peak < 22.0, deep_work != 45.0."""
        tracker = BehavioralTracker()
        beliefs = _make_beliefs()

        updated = tracker.on_self_scheduled(
            beliefs=beliefs,
            chosen_hour=10.0,
            duration_minutes=60,
        )

        peak = updated[BeliefParameter.PEAK_ENERGY].belief_value
        deep = updated[BeliefParameter.DEEP_WORK_TOLERANCE].belief_value
        assert peak < 22.0, f"peak_energy should be < 22.0, got {peak}"
        assert deep != 45.0, f"deep_work_tolerance should have shifted from 45.0, got {deep}"

    def test_track_energy_report(self) -> None:
        """Energy report 'great' at 10.0 -> peak < 22.0."""
        tracker = BehavioralTracker()
        beliefs = _make_beliefs()

        updated = tracker.on_energy_report(
            beliefs=beliefs,
            current_hour=10.0,
            level="great",
        )

        peak = updated[BeliefParameter.PEAK_ENERGY].belief_value
        assert peak < 22.0, f"peak_energy should be < 22.0 after 'great' at 10.0, got {peak}"
