from __future__ import annotations
"""BeliefUpdater Service — processes behavioral signals to update user beliefs."""

from enum import Enum

from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief


class SignalType(Enum):
    """Types of behavioral signals with associated weights."""

    BLOCK_COMPLETION = ("block_completion", 0.3)
    RESCHEDULE = ("reschedule", 0.4)
    SELF_SCHEDULED = ("self_scheduled", 0.2)
    ENERGY_SELF_REPORT = ("energy_self_report", 0.5)

    def __init__(self, label: str, weight: float) -> None:
        self._label = label
        self._weight = weight

    @property
    def label(self) -> str:
        return self._label

    @property
    def weight(self) -> float:
        return self._weight


ENERGY_REPORT_MAP: dict[str, float] = {
    "low": 0.3,
    "ok": 0.6,
    "great": 0.9,
}


def _opposite_hour(hour: float) -> float:
    """
    Compute the 'opposite' hour on a 24-hour clock.

    If hour > 12, opposite = hour - 12; otherwise opposite = hour + 12.
    This is used for skipped blocks to push the belief away from the skipped time.
    """
    if hour > 12.0:
        return hour - 12.0
    return hour + 12.0


class BeliefUpdater:
    """
    Processes behavioral signals and returns updated belief dictionaries.

    All methods return a new dict with updated UserBelief instances
    (no mutation of the input dict or its frozen dataclass values).
    """

    def process_block_completion(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        block_start_hour: float,
        block_duration_minutes: int,
        status: str,
        *,
        minutes_since_last_block: float | None = None,
        is_meeting_adjacent: bool = False,
    ) -> dict[BeliefParameter, UserBelief]:
        """
        Process a block completion or skip signal.

        For completed blocks:
          - peak_energy shifts toward the block's start hour.
          - deep_work_tolerance shifts toward the block's duration.
          - If minutes_since_last_block < 15: CONTEXT_SWITCH_COST shifts down.

        For skipped blocks:
          - peak_energy shifts toward the opposite hour (away from the skip time).
          - If is_meeting_adjacent: MEETING_TOLERANCE shifts down.

        Args:
            beliefs: Current belief dict.
            block_start_hour: Hour of day (0.0–23.99) when the block started.
            block_duration_minutes: Duration of the block in minutes.
            status: "completed" or "skipped".
            minutes_since_last_block: Minutes gap since the previous block ended.
            is_meeting_adjacent: Whether this block was adjacent to a meeting.

        Returns:
            New beliefs dict with updated values.
        """
        result = dict(beliefs)
        weight = SignalType.BLOCK_COMPLETION.weight

        if status == "completed":
            # Shift peak_energy toward block start hour
            result[BeliefParameter.PEAK_ENERGY] = beliefs[
                BeliefParameter.PEAK_ENERGY
            ].update(observation=block_start_hour, signal_weight=weight)

            # Shift deep_work_tolerance toward block duration
            result[BeliefParameter.DEEP_WORK_TOLERANCE] = beliefs[
                BeliefParameter.DEEP_WORK_TOLERANCE
            ].update(
                observation=float(block_duration_minutes), signal_weight=weight
            )

            # If back-to-back (< 15 min gap), signal low context switch cost
            if (
                minutes_since_last_block is not None
                and minutes_since_last_block < 15
            ):
                current_val = beliefs[BeliefParameter.CONTEXT_SWITCH_COST].belief_value
                obs = max(current_val - 0.15, 0.0)
                result[BeliefParameter.CONTEXT_SWITCH_COST] = beliefs[
                    BeliefParameter.CONTEXT_SWITCH_COST
                ].update(observation=obs, signal_weight=weight)

        elif status == "skipped":
            # Push peak_energy away from the skipped hour
            opposite = _opposite_hour(block_start_hour)
            result[BeliefParameter.PEAK_ENERGY] = beliefs[
                BeliefParameter.PEAK_ENERGY
            ].update(observation=opposite, signal_weight=weight)

            # If meeting-adjacent skip, signal low meeting tolerance
            if is_meeting_adjacent:
                current_val = beliefs[BeliefParameter.MEETING_TOLERANCE].belief_value
                obs = max(current_val - 0.15, 0.0)
                result[BeliefParameter.MEETING_TOLERANCE] = beliefs[
                    BeliefParameter.MEETING_TOLERANCE
                ].update(observation=obs, signal_weight=weight)

        return result

    def process_reschedule(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        original_hour: float,
        new_hour: float,
    ) -> dict[BeliefParameter, UserBelief]:
        """
        Process a reschedule signal — user moved a block from one time to another.

        Shifts peak_energy toward the new hour (the time the user preferred).

        Args:
            beliefs: Current belief dict.
            original_hour: The original scheduled hour.
            new_hour: The hour the user rescheduled to.

        Returns:
            New beliefs dict with updated peak_energy.
        """
        result = dict(beliefs)
        weight = SignalType.RESCHEDULE.weight

        result[BeliefParameter.PEAK_ENERGY] = beliefs[
            BeliefParameter.PEAK_ENERGY
        ].update(observation=new_hour, signal_weight=weight)

        return result

    def process_self_scheduled(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        chosen_hour: float,
        block_duration_minutes: int,
    ) -> dict[BeliefParameter, UserBelief]:
        """
        Process a self-scheduled block signal — user proactively created a block.

        Shifts peak_energy toward the chosen hour and deep_work_tolerance
        toward the chosen duration.

        Args:
            beliefs: Current belief dict.
            chosen_hour: Hour of day the user chose.
            block_duration_minutes: Duration the user selected.

        Returns:
            New beliefs dict with updated values.
        """
        result = dict(beliefs)
        weight = SignalType.SELF_SCHEDULED.weight

        result[BeliefParameter.PEAK_ENERGY] = beliefs[
            BeliefParameter.PEAK_ENERGY
        ].update(observation=chosen_hour, signal_weight=weight)

        result[BeliefParameter.DEEP_WORK_TOLERANCE] = beliefs[
            BeliefParameter.DEEP_WORK_TOLERANCE
        ].update(
            observation=float(block_duration_minutes), signal_weight=weight
        )

        return result

    def process_disruption_response(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        response: str,
    ) -> dict[BeliefParameter, UserBelief]:
        """
        Process a disruption response signal — how the user reacted to a disruption.

        Maps response type to a chaos_tolerance observation:
          - "rescheduled" → 0.2 (low tolerance)
          - "pushed_through" → 0.8 (high tolerance)
          - "cancelled" → 0.1 (very low tolerance)

        Args:
            beliefs: Current belief dict.
            response: One of 'rescheduled', 'pushed_through', 'cancelled'.

        Returns:
            New beliefs dict with updated chaos_tolerance.
        """
        result = dict(beliefs)
        obs_map = {
            "rescheduled": 0.2,
            "pushed_through": 0.8,
            "cancelled": 0.1,
        }
        obs = obs_map.get(response, 0.5)
        weight = SignalType.RESCHEDULE.weight

        result[BeliefParameter.CHAOS_TOLERANCE] = beliefs[
            BeliefParameter.CHAOS_TOLERANCE
        ].update(observation=obs, signal_weight=weight)

        return result

    def process_recovery_signal(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        gap_hours: float,
    ) -> dict[BeliefParameter, UserBelief]:
        """
        Process a recovery signal — infer recovery rate from gap between blocks.

        Gaps > 4.0 hours are ignored (too long to be meaningful recovery data).
        For shorter gaps, observation = min(0.20, 1.0 / max(gap_hours, 0.25) * 0.05).

        Args:
            beliefs: Current belief dict.
            gap_hours: Hours between end of last block and start of next.

        Returns:
            New beliefs dict (unchanged if gap > 4.0).
        """
        result = dict(beliefs)

        if gap_hours > 4.0:
            return result

        obs = min(0.20, 1.0 / max(gap_hours, 0.25) * 0.05)
        weight = SignalType.BLOCK_COMPLETION.weight

        result[BeliefParameter.RECOVERY_RATE] = beliefs[
            BeliefParameter.RECOVERY_RATE
        ].update(observation=obs, signal_weight=weight)

        return result

    def process_energy_report(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        current_hour: float,
        level: str,
    ) -> dict[BeliefParameter, UserBelief]:
        """
        Process an energy self-report signal.

        Only updates peak_energy if the reported energy level is >= 0.7
        (i.e., 'great'). Lower levels ('ok', 'low') are not strong enough
        signals to shift the peak energy belief.

        Args:
            beliefs: Current belief dict.
            current_hour: Hour of day when the report was made.
            level: One of 'low', 'ok', 'great'.

        Returns:
            New beliefs dict (possibly unchanged if level < 0.7).
        """
        result = dict(beliefs)
        energy_value = ENERGY_REPORT_MAP.get(level, 0.5)

        if energy_value >= 0.7:
            weight = SignalType.ENERGY_SELF_REPORT.weight
            result[BeliefParameter.PEAK_ENERGY] = beliefs[
                BeliefParameter.PEAK_ENERGY
            ].update(observation=current_hour, signal_weight=weight)

        return result
