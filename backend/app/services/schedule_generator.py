"""
Schedule Generator - Deterministic solver for schedule creation.

Uses Anchor-and-Fill strategy:
1. Place anchor task in peak energy window
2. Inject cognitive buffers
3. Bin-pack remaining tasks
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from app.models.onboarding import (
    AccumulatedSession,
    ExtractedTask,
    TaskIntentType,
    TaskPriority,
    UserProfile,
)
from app.models.scheduling_context import SchedulingContext
from app.models.timeline import ScheduledBlock


@dataclass
class GeneratedSchedule:
    """A generated schedule with metadata."""
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
    
    # Scheduled blocks
    blocks: List[ScheduledBlock] = field(default_factory=list)
    
    # Overflow - tasks that didn't fit
    overflow_tasks: List[ExtractedTask] = field(default_factory=list)
    
    # Confidence and metadata
    confidence: float = 0.8
    anchor_task_id: Optional[UUID] = None
    total_scheduled_minutes: int = 0
    
    @property
    def has_overflow(self) -> bool:
        return len(self.overflow_tasks) > 0


class ScheduleGenerator:
    """
    Deterministic schedule solver.
    
    Does NOT:
    - Use LLM for placement decisions
    - Make priority judgments
    - Negotiate with user
    
    Does:
    - Place anchor in peak window
    - Inject buffers after high-load tasks
    - Bin-pack remaining slots
    """
    
    # Buffer durations by task type
    BUFFER_AFTER_HIGH_LOAD = 15  # minutes
    BUFFER_AFTER_MEETING = 10
    MIN_BLOCK_SIZE = 15
    
    def generate(
        self,
        session: AccumulatedSession,
        target_date: datetime,
        start_time: Optional[datetime] = None,
        fixed_blocks: Optional[List[ScheduledBlock]] = None,
        scheduling_context: Optional[SchedulingContext] = None,
    ) -> GeneratedSchedule:
        """
        Generate a schedule for the given date.

        Strategy:
        1. Get anchor task (highest priority) -> only if start_time not set (fresh day)
        2. Place anchor in peak energy window
        3. Add cognitive buffers
        4. Bin-pack remaining tasks
        5. Report overflow

        If start_time is set (replanning):
        - Respect fixed_blocks (don't schedule over them)
        - Only schedule tasks that haven't been completed (assumed passed in session)
        - Skip Anchor logic if peak window passed? Or try to fit it in remaining.

        If scheduling_context is provided:
        - peak_energy_start/end override the profile's peak window
        - max_block_duration_minutes caps each block's duration
        - min_buffer_minutes overrides the buffer after high-load tasks
        """
        if not session.profile:
            raise ValueError("Profile required for schedule generation")

        profile = session.profile
        tasks = session.extracted_tasks.copy()
        schedule = GeneratedSchedule(user_id=session.user_id)

        # Apply scheduling_context overrides
        if scheduling_context:
            if scheduling_context.min_buffer_minutes:
                self._buffer_after_high_load = max(
                    self.BUFFER_AFTER_HIGH_LOAD,
                    int(scheduling_context.min_buffer_minutes),
                )
            else:
                self._buffer_after_high_load = self.BUFFER_AFTER_HIGH_LOAD
            self._max_block_duration = (
                int(scheduling_context.max_block_duration_minutes)
                if scheduling_context.max_block_duration_minutes
                else None
            )
        else:
            self._buffer_after_high_load = self.BUFFER_AFTER_HIGH_LOAD
            self._max_block_duration = None
        
        # If fixed blocks provided, add them to result
        if fixed_blocks:
            schedule.blocks.extend(fixed_blocks)
            
        if not tasks:
            return schedule
        
        # 1. Find anchor task
        anchor = self._get_anchor_task(tasks)
        if anchor:
            tasks.remove(anchor)
            if not start_time: # Only mark separate anchor on fresh day
                schedule.anchor_task_id = anchor.id
        
        # 2. Build available slots for the day
        slots = self._build_available_slots(profile, target_date, start_time, fixed_blocks)
        
        # 3. Place anchor (try peak window first)
        if anchor:
            placed_anchor = False
            # Try peak window if available and valid
            peak_slot = self._find_peak_slot(slots, profile, target_date, scheduling_context)
            
            if peak_slot:
                block = self._create_block(anchor, peak_slot[0], session.user_id)
                schedule.blocks.append(block)
                schedule.total_scheduled_minutes += anchor.estimated_minutes

                # Add buffer after anchor if high load
                if anchor.is_high_load:
                    buffer_end = peak_slot[0] + timedelta(
                        minutes=anchor.estimated_minutes + self._buffer_after_high_load
                    )
                    slots = self._remove_time_range(
                        slots, peak_slot[0], buffer_end
                    )
                else:
                    slots = self._remove_time_range(
                        slots,
                        peak_slot[0],
                        peak_slot[0] + timedelta(minutes=anchor.estimated_minutes)
                    )
                placed_anchor = True
            
            # If couldn't place in peak (e.g. replanning in afternoon), treat as normal task
            if not placed_anchor:
                tasks.insert(0, anchor) # Put back at top of list
        
        # 4. Sort remaining tasks by priority and theme alignment
        # Invariant #5: Theme acts as tie-breaker
        # We need to score theme alignment. For now, we'll assume the extraction 
        # phase could add a 'relevance_to_theme' score, or we do a simple heuristic.
        # Since we don't have semantic embeddings yet, we'll rely on strict priority first.
        # Future improvement: Add 'theme_alignment' float to ExtractedTask
        
        tasks.sort(key=lambda t: (
            0 if t.priority == TaskPriority.MUST_DO else
            1 if t.priority == TaskPriority.SHOULD_DO else 2,
            
            # Secondary sort: Estimated duration (Longer tasks first? Or shorter?)
            # Heuristic: Schedule big rocks first
            -t.estimated_minutes
        ))
        
        # 5. Bin-pack remaining tasks
        for task in tasks:
            placed = False
            duration = task.estimated_minutes

            # Cap duration if scheduling_context constrains it
            if self._max_block_duration:
                duration = min(duration, self._max_block_duration)

            # Add buffer if high load
            if task.is_high_load:
                duration += self._buffer_after_high_load
            
            for slot_start, slot_end in slots:
                slot_duration = (slot_end - slot_start).total_seconds() / 60
                
                if slot_duration >= duration:
                    block = self._create_block(task, slot_start, session.user_id)
                    schedule.blocks.append(block)
                    schedule.total_scheduled_minutes += task.estimated_minutes
                    
                    # Remove used time from slots
                    slots = self._remove_time_range(
                        slots, 
                        slot_start, 
                        slot_start + timedelta(minutes=duration)
                    )
                    placed = True
                    break
            
            if not placed:
                schedule.overflow_tasks.append(task)
        
        # Sort blocks by start time
        schedule.blocks.sort(key=lambda b: b.start_time)
        
        # Compute confidence
        if session.extracted_tasks:
            placed_count = len(schedule.blocks)
            total_count = len(session.extracted_tasks)
            schedule.confidence = placed_count / total_count
        
        return schedule
    
    def _get_anchor_task(self, tasks: List[ExtractedTask]) -> Optional[ExtractedTask]:
        """Get the highest priority task as anchor."""
        must_do = [t for t in tasks if t.priority == TaskPriority.MUST_DO]
        if must_do:
            # Prefer longest must-do task
            return max(must_do, key=lambda t: t.estimated_minutes)
        
        should_do = [t for t in tasks if t.priority == TaskPriority.SHOULD_DO]
        if should_do:
            return max(should_do, key=lambda t: t.estimated_minutes)
        
        return tasks[0] if tasks else None
    
    def _build_available_slots(
        self, 
        profile: UserProfile, 
        target_date: datetime,
        start_time: Optional[datetime] = None,
        fixed_blocks: Optional[List[ScheduledBlock]] = None,
    ) -> List[Tuple[datetime, datetime]]:
        """Build list of available time slots for the day."""
        work_start = datetime.combine(target_date.date(), profile.work_start)
        work_end = datetime.combine(target_date.date(), profile.work_end)
        
        # If replanning, start from provided time (clamped to work hours)
        if start_time:
            current_start = max(work_start, start_time)
        else:
            current_start = work_start
            
        if current_start >= work_end:
            return []
            
        slots = [(current_start, work_end)]
        
        # Remove fixed blocks
        if fixed_blocks:
            for block in fixed_blocks:
                slots = self._remove_time_range(slots, block.start_time, block.end_time)
        
        return slots
    
    def _find_peak_slot(
        self,
        slots: List[Tuple[datetime, datetime]],
        profile: UserProfile,
        target_date: datetime,
        scheduling_context: Optional[SchedulingContext] = None,
    ) -> Optional[Tuple[datetime, datetime]]:
        """Find a slot within peak energy window.

        If scheduling_context is provided, its peak_energy_start/end (float hours)
        override the profile's peak window.
        """
        if scheduling_context:
            # Convert float hours to time objects
            ps_hour = int(scheduling_context.peak_energy_start)
            ps_min = int((scheduling_context.peak_energy_start - ps_hour) * 60)
            pe_hour = int(scheduling_context.peak_energy_end)
            pe_min = int((scheduling_context.peak_energy_end - pe_hour) * 60)
            peak_start = datetime.combine(target_date.date(), time(max(0, ps_hour), max(0, ps_min)))
            peak_end = datetime.combine(target_date.date(), time(min(23, pe_hour), max(0, pe_min)))
        else:
            peak_start = datetime.combine(target_date.date(), profile.peak_energy_start)
            peak_end = datetime.combine(target_date.date(), profile.peak_energy_end)
        
        for slot_start, slot_end in slots:
            # Check if slot overlaps with peak window
            overlap_start = max(slot_start, peak_start)
            overlap_end = min(slot_end, peak_end)
            
            if overlap_start < overlap_end:
                return (overlap_start, overlap_end)
        
        # Fallback to first available slot
        return slots[0] if slots else None
    
    def _remove_time_range(
        self,
        slots: List[Tuple[datetime, datetime]],
        remove_start: datetime,
        remove_end: datetime,
    ) -> List[Tuple[datetime, datetime]]:
        """Remove a time range from available slots."""
        new_slots = []
        
        for slot_start, slot_end in slots:
            if remove_end <= slot_start or remove_start >= slot_end:
                # No overlap
                new_slots.append((slot_start, slot_end))
            else:
                # Split the slot
                if slot_start < remove_start:
                    new_slots.append((slot_start, remove_start))
                if remove_end < slot_end:
                    new_slots.append((remove_end, slot_end))
        
        return new_slots
    
    def _create_block(
        self,
        task: ExtractedTask,
        start_time: datetime,
        user_id: UUID,
    ) -> ScheduledBlock:
        """Create a scheduled block from a task."""
        # Cap task duration if scheduling_context constrains it
        effective_minutes = task.estimated_minutes
        if getattr(self, "_max_block_duration", None):
            effective_minutes = min(effective_minutes, self._max_block_duration)

        end_time = start_time + timedelta(minutes=effective_minutes)

        # Map intent type to activity nature
        activity_nature = {
            TaskIntentType.OUTCOME_ORIENTED: "DEEP_WORK",
            TaskIntentType.TIME_ORIENTED: "SHALLOW_WORK",
            TaskIntentType.MAINTENANCE: "ADMIN",
        }.get(task.intent_type, "SHALLOW_WORK")

        buffer_after = getattr(self, "_buffer_after_high_load", self.BUFFER_AFTER_HIGH_LOAD)

        return ScheduledBlock(
            user_id=user_id,
            intent_id=task.id,
            start_time=start_time,
            end_time=end_time,
            goal=task.name,
            activity_nature=activity_nature,
            buffer_before_minutes=0,
            buffer_after_minutes=buffer_after if task.is_high_load else 0,
            is_locked=task.priority == TaskPriority.MUST_DO,
        )


# Singleton instance
schedule_generator = ScheduleGenerator()
