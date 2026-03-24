from __future__ import annotations
"""Tests for BeliefUpdater service — signal processing for all 4 signal types."""

from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief
from app.services.belief_updater import BeliefUpdater, SignalType


def _make_beliefs() -> dict[BeliefParameter, UserBelief]:
    """Create a default beliefs dict matching the Student role defaults."""
    defaults: dict[BeliefParameter, float] = {
        BeliefParameter.PEAK_ENERGY: 22.0,
        BeliefParameter.DEEP_WORK_TOLERANCE: 45.0,
        BeliefParameter.CONTEXT_SWITCH_COST: 0.7,
        BeliefParameter.CHAOS_TOLERANCE: 0.4,
        BeliefParameter.MEETING_TOLERANCE: 0.3,
        BeliefParameter.RECOVERY_RATE: 0.15,
        BeliefParameter.GUIDANCE_LEVEL: 0.5,
    }
    return {
        param: UserBelief(parameter=param, belief_value=value)
        for param, value in defaults.items()
    }


class TestSignalTypeWeights:
    """Verify signal type weights are correctly defined."""

    def test_block_completion_weight(self) -> None:
        assert SignalType.BLOCK_COMPLETION.weight == 0.3

    def test_reschedule_weight(self) -> None:
        assert SignalType.RESCHEDULE.weight == 0.4

    def test_self_scheduled_weight(self) -> None:
        assert SignalType.SELF_SCHEDULED.weight == 0.2

    def test_energy_self_report_weight(self) -> None:
        assert SignalType.ENERGY_SELF_REPORT.weight == 0.5


class TestProcessBlockCompletion:
    """Test block completion signal processing."""

    def test_completed_block_shifts_peak_energy_toward_block_hour(self) -> None:
        """Block at 14:00, 45 min, completed → peak_energy shifts toward 14.0 (< 22.0)."""
        beliefs = _make_beliefs()
        updater = BeliefUpdater()

        result = updater.process_block_completion(
            beliefs=beliefs,
            block_start_hour=14.0,
            block_duration_minutes=45,
            status="completed",
        )

        # Peak energy should shift toward 14.0 (currently 22.0)
        assert result[BeliefParameter.PEAK_ENERGY].belief_value < 22.0
        # Deep work tolerance should stay near 45.0 (block was 45 min)
        assert abs(result[BeliefParameter.DEEP_WORK_TOLERANCE].belief_value - 45.0) < 2.0

    def test_completed_block_returns_new_dict(self) -> None:
        """Result should be a new dict, not a mutation of the original."""
        beliefs = _make_beliefs()
        updater = BeliefUpdater()

        result = updater.process_block_completion(
            beliefs=beliefs,
            block_start_hour=14.0,
            block_duration_minutes=45,
            status="completed",
        )

        assert result is not beliefs
        # Original beliefs should be unchanged (frozen dataclass)
        assert beliefs[BeliefParameter.PEAK_ENERGY].belief_value == 22.0


class TestProcessBlockSkipped:
    """Test skipped block signal processing."""

    def test_skipped_block_moves_peak_energy_away(self) -> None:
        """Block at 22.0, skipped → peak_energy moves away (opposite = 10.0 since 22 > 12)."""
        beliefs = _make_beliefs()
        updater = BeliefUpdater()

        result = updater.process_block_completion(
            beliefs=beliefs,
            block_start_hour=22.0,
            block_duration_minutes=45,
            status="skipped",
        )

        # opposite_of(22.0) = 10.0 (since 22 > 12, opposite = 22 - 12 = 10)
        # So peak energy should move away from 22.0, toward 10.0
        # Current mean is 22.0, so it should decrease
        assert result[BeliefParameter.PEAK_ENERGY].belief_value < 22.0


class TestProcessReschedule:
    """Test reschedule signal processing."""

    def test_reschedule_shifts_peak_toward_new_hour(self) -> None:
        """Rescheduling from 22.0 to 15.0 → peak shifts toward 15.0."""
        beliefs = _make_beliefs()
        updater = BeliefUpdater()

        result = updater.process_reschedule(
            beliefs=beliefs,
            original_hour=22.0,
            new_hour=15.0,
        )

        # Peak energy (22.0) should shift toward 15.0
        assert result[BeliefParameter.PEAK_ENERGY].belief_value < 22.0

    def test_reschedule_returns_new_dict(self) -> None:
        beliefs = _make_beliefs()
        updater = BeliefUpdater()

        result = updater.process_reschedule(
            beliefs=beliefs,
            original_hour=22.0,
            new_hour=15.0,
        )

        assert result is not beliefs


class TestProcessEnergyReport:
    """Test energy self-report signal processing."""

    def test_great_energy_shifts_peak_toward_current_hour(self) -> None:
        """'great' at hour 14.0 → peak shifts toward 14.0."""
        beliefs = _make_beliefs()
        updater = BeliefUpdater()

        result = updater.process_energy_report(
            beliefs=beliefs,
            current_hour=14.0,
            level="great",
        )

        # Peak energy (22.0) should shift toward 14.0
        assert result[BeliefParameter.PEAK_ENERGY].belief_value < 22.0

    def test_low_energy_does_not_shift_peak(self) -> None:
        """'low' energy (0.3 < 0.7) should not update peak_energy."""
        beliefs = _make_beliefs()
        updater = BeliefUpdater()

        result = updater.process_energy_report(
            beliefs=beliefs,
            current_hour=14.0,
            level="low",
        )

        # Peak energy should remain unchanged
        assert result[BeliefParameter.PEAK_ENERGY].belief_value == 22.0

    def test_ok_energy_shifts_peak(self) -> None:
        """'ok' energy (0.6 < 0.7) should not update peak_energy."""
        beliefs = _make_beliefs()
        updater = BeliefUpdater()

        result = updater.process_energy_report(
            beliefs=beliefs,
            current_hour=14.0,
            level="ok",
        )

        # 'ok' = 0.6, which is < 0.7, so no update
        assert result[BeliefParameter.PEAK_ENERGY].belief_value == 22.0


class TestContextSwitchCost:
    """Test context switch cost updates from back-to-back blocks."""

    def test_context_switch_cost_from_back_to_back(self) -> None:
        """Back-to-back completed block = low switch cost signal."""
        updater = BeliefUpdater()
        beliefs = _make_beliefs()
        updated = updater.process_block_completion(
            beliefs=beliefs,
            block_start_hour=14.0,
            block_duration_minutes=45,
            status="completed",
            minutes_since_last_block=5,
        )
        assert updated[BeliefParameter.CONTEXT_SWITCH_COST].belief_value < 0.7


class TestChaosTolerance:
    """Test chaos tolerance updates from disruption responses."""

    def test_chaos_tolerance_from_disruption(self) -> None:
        updater = BeliefUpdater()
        beliefs = _make_beliefs()
        updated = updater.process_disruption_response(
            beliefs=beliefs, response="rescheduled"
        )
        assert updated[BeliefParameter.CHAOS_TOLERANCE].belief_value < 0.4


class TestMeetingTolerance:
    """Test meeting tolerance updates from meeting-adjacent skips."""

    def test_meeting_tolerance_skip_adjacent(self) -> None:
        updater = BeliefUpdater()
        beliefs = _make_beliefs()
        updated = updater.process_block_completion(
            beliefs=beliefs,
            block_start_hour=14.0,
            block_duration_minutes=30,
            status="skipped",
            is_meeting_adjacent=True,
        )
        assert updated[BeliefParameter.MEETING_TOLERANCE].belief_value < 0.3


class TestRecoveryRate:
    """Test recovery rate updates from gap signals."""

    def test_recovery_rate_from_gap(self) -> None:
        updater = BeliefUpdater()
        beliefs = _make_beliefs()
        updated = updater.process_recovery_signal(
            beliefs=beliefs, gap_hours=1.0
        )
        assert updated[BeliefParameter.RECOVERY_RATE].evidence_count == 1

    def test_recovery_rate_ignores_long_gaps(self) -> None:
        updater = BeliefUpdater()
        beliefs = _make_beliefs()
        updated = updater.process_recovery_signal(
            beliefs=beliefs, gap_hours=5.0
        )
        assert updated[BeliefParameter.RECOVERY_RATE].evidence_count == 0
