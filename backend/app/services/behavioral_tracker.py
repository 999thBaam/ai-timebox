"""BehavioralTracker Service — routes behavioral signals through BeliefUpdater."""

from __future__ import annotations

from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief
from app.services.belief_updater import BeliefUpdater


class BehavioralTracker:
    """
    High-level facade that translates UI/API events into belief updates.

    Wraps a BeliefUpdater instance and exposes intent-named methods
    (on_block_status_change, on_reschedule, etc.) so callers don't need
    to know which low-level updater method to invoke.
    """

    def __init__(self, updater: BeliefUpdater | None = None) -> None:
        self._updater = updater or BeliefUpdater()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on_block_status_change(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        block_start_hour: float,
        block_duration_minutes: int,
        new_status: str,
    ) -> dict[BeliefParameter, UserBelief]:
        """Route a block completion/skip event to the updater.

        Args:
            beliefs: Current belief dict.
            block_start_hour: Hour of day (0.0-23.99) when the block started.
            block_duration_minutes: Duration of the block in minutes.
            new_status: "completed" or "skipped".

        Returns:
            New beliefs dict with updated values.
        """
        return self._updater.process_block_completion(
            beliefs=beliefs,
            block_start_hour=block_start_hour,
            block_duration_minutes=block_duration_minutes,
            status=new_status,
        )

    def on_reschedule(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        original_hour: float,
        new_hour: float,
    ) -> dict[BeliefParameter, UserBelief]:
        """Route a reschedule event to the updater.

        Args:
            beliefs: Current belief dict.
            original_hour: The original scheduled hour.
            new_hour: The hour the user rescheduled to.

        Returns:
            New beliefs dict with updated peak_energy.
        """
        return self._updater.process_reschedule(
            beliefs=beliefs,
            original_hour=original_hour,
            new_hour=new_hour,
        )

    def on_self_scheduled(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        chosen_hour: float,
        duration_minutes: int,
    ) -> dict[BeliefParameter, UserBelief]:
        """Route a self-scheduled block event to the updater.

        Args:
            beliefs: Current belief dict.
            chosen_hour: Hour of day the user chose.
            duration_minutes: Duration the user selected.

        Returns:
            New beliefs dict with updated values.
        """
        return self._updater.process_self_scheduled(
            beliefs=beliefs,
            chosen_hour=chosen_hour,
            block_duration_minutes=duration_minutes,
        )

    def on_energy_report(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        current_hour: float,
        level: str,
    ) -> dict[BeliefParameter, UserBelief]:
        """Route an energy self-report event to the updater.

        Args:
            beliefs: Current belief dict.
            current_hour: Hour of day when the report was made.
            level: One of 'low', 'ok', 'great'.

        Returns:
            New beliefs dict (possibly unchanged if level < 0.7).
        """
        return self._updater.process_energy_report(
            beliefs=beliefs,
            current_hour=current_hour,
            level=level,
        )
