from __future__ import annotations
"""
Planner Engine - Core scheduling brain of AI Timebox.

Responsibilities:
1. Generate multiple candidate timelines
2. Simulate human state trajectories for each
3. Score candidates on goal fulfillment, safety, stability
4. Select the best plan that keeps user within safe bounds
"""
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from app.models.intent import IntentHypothesis, ActivityNature, EnergyLevel
from app.models.human_state import HumanState
from app.models.safety_policy import SafetyPolicy
from app.models.timeline import ScheduledBlock, CandidateTimeline, StateCheckpoint
from app.models.planner import PlannerExplanation, PlannerResult


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVITY IMPACT PROFILES
# ═══════════════════════════════════════════════════════════════════════════════

ACTIVITY_IMPACTS: dict[ActivityNature, dict] = {
    ActivityNature.DEEP_WORK: {
        "cognitive_cost": 0.3,
        "energy_cost": 0.25,
        "residue": 0.4,
        "ramp_up": 15,
        "cool_down": 10,
    },
    ActivityNature.SHALLOW_WORK: {
        "cognitive_cost": 0.1,
        "energy_cost": 0.1,
        "residue": 0.15,
        "ramp_up": 5,
        "cool_down": 5,
    },
    ActivityNature.MEETING: {
        "cognitive_cost": 0.2,
        "energy_cost": 0.2,
        "residue": 0.3,
        "ramp_up": 5,
        "cool_down": 10,
    },
    ActivityNature.BREAK: {
        "cognitive_cost": -0.2,  # Negative = recovery
        "energy_cost": -0.15,
        "residue": 0.0,
        "ramp_up": 0,
        "cool_down": 0,
    },
    ActivityNature.PERSONAL: {
        "cognitive_cost": 0.15,
        "energy_cost": 0.15,
        "residue": 0.2,
        "ramp_up": 5,
        "cool_down": 5,
    },
    ActivityNature.ADMIN: {
        "cognitive_cost": 0.1,
        "energy_cost": 0.1,
        "residue": 0.1,
        "ramp_up": 5,
        "cool_down": 5,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# CANDIDATE GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_candidate_slots(
    hypothesis: IntentHypothesis,
    existing_blocks: list[ScheduledBlock],
    day_start: datetime,
    day_end: datetime,
    num_candidates: int = 5,
) -> list[tuple[datetime, datetime]]:
    """
    Generate candidate time slots for scheduling.
    
    Strategy:
    1. Find all free windows
    2. Prefer windows that match preferred time of day
    3. Prefer windows with natural buffer space
    """
    duration = timedelta(minutes=hypothesis.duration_estimate_minutes)
    impact = ACTIVITY_IMPACTS.get(hypothesis.activity_nature, ACTIVITY_IMPACTS[ActivityNature.SHALLOW_WORK])
    buffer_before = timedelta(minutes=impact["ramp_up"])
    buffer_after = timedelta(minutes=impact["cool_down"])
    total_needed = buffer_before + duration + buffer_after

    # Sort existing blocks by start time
    sorted_blocks = sorted(existing_blocks, key=lambda b: b.start_time)

    # Find free windows
    free_windows: list[tuple[datetime, datetime]] = []
    current = day_start

    for block in sorted_blocks:
        # Account for buffer after previous block
        block_start_with_buffer = block.start_time - timedelta(minutes=block.buffer_before_minutes)
        if current < block_start_with_buffer:
            window_duration = block_start_with_buffer - current
            if window_duration >= total_needed:
                free_windows.append((current, block_start_with_buffer))
        current = block.end_time + timedelta(minutes=block.buffer_after_minutes)

    # Window after last block
    if current < day_end:
        window_duration = day_end - current
        if window_duration >= total_needed:
            free_windows.append((current, day_end))

    # Generate candidate slots from free windows
    candidates: list[tuple[datetime, datetime]] = []

    for window_start, window_end in free_windows:
        # Start of window
        slot_start = window_start + buffer_before
        slot_end = slot_start + duration
        if slot_end + buffer_after <= window_end:
            candidates.append((slot_start, slot_end))

        # Middle of window
        window_duration = window_end - window_start
        if window_duration >= total_needed * 2:
            mid_start = window_start + (window_duration - duration) / 2
            mid_end = mid_start + duration
            if mid_start >= window_start + buffer_before and mid_end + buffer_after <= window_end:
                candidates.append((mid_start, mid_end))

        # End of window
        slot_end = window_end - buffer_after
        slot_start = slot_end - duration
        if slot_start >= window_start + buffer_before:
            candidates.append((slot_start, slot_end))

    # Remove duplicates and limit
    seen = set()
    unique_candidates = []
    for c in candidates:
        key = (c[0].isoformat(), c[1].isoformat())
        if key not in seen:
            seen.add(key)
            unique_candidates.append(c)

    return unique_candidates[:num_candidates]


# ═══════════════════════════════════════════════════════════════════════════════
# STATE SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_block_impact(
    state: HumanState,
    block: ScheduledBlock,
    activity_nature: ActivityNature,
) -> tuple[HumanState, list[StateCheckpoint]]:
    """
    Simulate the impact of a scheduled block on human state.
    
    Returns:
        Updated state after block completion
        List of checkpoints (START, PEAK_LOAD, END)
    """
    impact = ACTIVITY_IMPACTS.get(activity_nature, ACTIVITY_IMPACTS[ActivityNature.SHALLOW_WORK])
    checkpoints: list[StateCheckpoint] = []

    # START checkpoint
    checkpoints.append(StateCheckpoint(
        timestamp=block.start_time,
        checkpoint_type="START",
        cognitive_load=state.cognitive_load,
        energy_level=state.energy_level,
        context_residue=state.context_residue,
    ))

    # Apply task impact
    mid_state = state.with_task_impact(
        cognitive_cost=impact["cognitive_cost"],
        energy_cost=impact["energy_cost"],
        residue=impact["residue"],
    )

    # PEAK_LOAD checkpoint (during task)
    checkpoints.append(StateCheckpoint(
        timestamp=block.start_time + (block.end_time - block.start_time) / 2,
        checkpoint_type="PEAK_LOAD",
        cognitive_load=mid_state.cognitive_load,
        energy_level=mid_state.energy_level,
        context_residue=mid_state.context_residue,
    ))

    # Apply decay for cool-down period
    end_time = block.end_time + timedelta(minutes=block.buffer_after_minutes)
    final_state = mid_state.with_decay(end_time)

    # END checkpoint
    checkpoints.append(StateCheckpoint(
        timestamp=end_time,
        checkpoint_type="END",
        cognitive_load=final_state.cognitive_load,
        energy_level=final_state.energy_level,
        context_residue=final_state.context_residue,
    ))

    return replace(final_state, updated_at=end_time), checkpoints


def simulate_timeline(
    initial_state: HumanState,
    new_block: ScheduledBlock,
    activity_nature: ActivityNature,
    existing_blocks: list[ScheduledBlock],
) -> tuple[float, float, list[StateCheckpoint]]:
    """
    Simulate the full timeline and compute safety score.
    
    Returns:
        min_safety_margin: Lowest safety margin throughout timeline
        peak_load: Maximum cognitive load reached
        checkpoints: State checkpoints for the new block
    """
    # Get state at the time of the new block
    state = initial_state.with_decay(new_block.start_time)

    # Simulate the new block
    final_state, checkpoints = simulate_block_impact(state, new_block, activity_nature)

    # Compute safety metrics
    min_margin = min(
        1.0 - checkpoints[1].cognitive_load,  # Use PEAK_LOAD
        checkpoints[1].energy_level,
    )
    peak_load = checkpoints[1].cognitive_load

    return min_margin, peak_load, checkpoints


# ═══════════════════════════════════════════════════════════════════════════════
# SAFETY VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def check_safety(
    candidate: CandidateTimeline,
    checkpoints: list[StateCheckpoint],
    policies: list[SafetyPolicy],
    now: datetime,
) -> list[UUID]:
    """
    Check which safety policies would be violated by this candidate.
    
    Returns list of violated policy IDs.
    """
    violations: list[UUID] = []

    # Create a temporary HumanState from peak checkpoint
    peak = next((c for c in checkpoints if c.checkpoint_type == "PEAK_LOAD"), None)
    if not peak:
        return violations

    # Create mock state for policy evaluation
    mock_state = HumanState(
        user_id=uuid4(),
        updated_at=peak.timestamp,
        cognitive_load=peak.cognitive_load,
        emotional_load=0.2,
        energy_level=peak.energy_level,
        context_residue=peak.context_residue,
        confidence=0.5,
        fragility=0.3,
        chaos_tolerance=0.5,
    )

    for policy in policies:
        if policy.is_active(mock_state, now):
            violations.append(policy.id)

    return violations


# ═══════════════════════════════════════════════════════════════════════════════
# SCORING
# ═══════════════════════════════════════════════════════════════════════════════

def score_candidate(
    candidate: CandidateTimeline,
    hypothesis: IntentHypothesis,
    preferred_hour: int | None = None,
) -> float:
    """
    Compute overall score for a candidate timeline.
    
    Weights:
    - Goal fulfillment: 40%
    - State safety: 40%
    - Stability: 20%
    """
    # Goal fulfillment: always 1.0 if we scheduled it
    goal_score = 1.0

    # Time preference bonus
    if preferred_hour is not None and candidate.blocks:
        block_hour = candidate.blocks[0].start_time.hour
        hour_diff = abs(block_hour - preferred_hour)
        time_bonus = max(0, 0.2 - (hour_diff * 0.05))
        goal_score += time_bonus

    candidate.goal_fulfillment = min(1.0, goal_score)
    candidate.stability_score = hypothesis.volatility.stability_score

    return candidate.compute_overall_score()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPLANATION GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_explanation(
    selected: CandidateTimeline,
    hypothesis: IntentHypothesis,
    rejected: list[tuple[CandidateTimeline, str]],
) -> PlannerExplanation:
    """
    Generate structured explanation facts for the selected plan.
    """
    reasons: list[str] = []
    avoided: list[str] = []
    tradeoffs: list[str] = []

    # Why this slot
    if selected.state_safety_score > 0.5:
        reasons.append("good_energy_alignment")
    if selected.blocks:
        block = selected.blocks[0]
        hour = block.start_time.hour
        if 9 <= hour <= 11:
            reasons.append("morning_focus_window")
        elif 14 <= hour <= 16:
            reasons.append("afternoon_energy_peak")

    # What we avoided
    for _, rejection_reason in rejected:
        if "overload" in rejection_reason.lower():
            avoided.append("cognitive_overload")
        if "back_to_back" in rejection_reason.lower():
            avoided.append("back_to_back_deep_work")

    # Tradeoffs
    if selected.blocks and hypothesis.preferred_window:
        pref_start, pref_end = hypothesis.preferred_window
        block_hour = selected.blocks[0].start_time.hour
        if not (pref_start.hour <= block_hour <= pref_end.hour):
            tradeoffs.append("scheduled_outside_preferred_window")

    return PlannerExplanation(
        reasons=reasons if reasons else ["available_slot"],
        avoided=avoided,
        tradeoffs=tradeoffs,
        confidence=selected.overall_score,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PLANNER ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

async def plan(
    user_id: UUID,
    hypothesis: IntentHypothesis,
    current_state: HumanState,
    existing_blocks: list[ScheduledBlock],
    policies: list[SafetyPolicy],
    target_date: datetime | None = None,
) -> PlannerResult:
    """
    Main planner entry point.
    
    Generates candidates, simulates each, scores them, and selects the best.
    """
    now = datetime.now()
    target_date = target_date or now

    # Define planning window
    day_start = target_date.replace(hour=8, minute=0, second=0, microsecond=0)
    day_end = target_date.replace(hour=22, minute=0, second=0, microsecond=0)

    # If target is today and it's past 8am, start from now
    if target_date.date() == now.date() and now > day_start:
        day_start = now + timedelta(minutes=15)  # 15 min buffer from now

    # Generate candidate time slots
    slots = generate_candidate_slots(
        hypothesis=hypothesis,
        existing_blocks=existing_blocks,
        day_start=day_start,
        day_end=day_end,
        num_candidates=5,
    )

    if not slots:
        return PlannerResult(
            candidates=[],
            selected=None,
            rejection_reasons={},
            explanation_facts=PlannerExplanation(
                reasons=["no_available_slots"],
                avoided=[],
                tradeoffs=[],
                confidence=0.0,
            ),
        )

    # Build and evaluate candidates
    candidates: list[CandidateTimeline] = []
    rejected: list[tuple[CandidateTimeline, str]] = []
    impact = ACTIVITY_IMPACTS.get(hypothesis.activity_nature, ACTIVITY_IMPACTS[ActivityNature.SHALLOW_WORK])

    for start_time, end_time in slots:
        # Create scheduled block
        block = ScheduledBlock(
            id=uuid4(),
            intent_id=hypothesis.id,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            goal=hypothesis.goal,
            activity_nature=hypothesis.activity_nature.value,
            buffer_before_minutes=impact["ramp_up"],
            buffer_after_minutes=impact["cool_down"],
            is_locked=False,
        )

        # Simulate
        safety_margin, peak_load, checkpoints = simulate_timeline(
            initial_state=current_state,
            new_block=block,
            activity_nature=hypothesis.activity_nature,
            existing_blocks=existing_blocks,
        )

        # Check safety policies
        violations = check_safety(
            candidate=CandidateTimeline(),
            checkpoints=checkpoints,
            policies=policies,
            now=now,
        )

        # Build candidate
        candidate = CandidateTimeline(
            id=uuid4(),
            created_at=now,
            blocks=[block],
            state_safety_score=safety_margin,
            state_checkpoints=checkpoints,
            violated_policies=violations,
        )

        # Score
        score_candidate(candidate, hypothesis)

        # Reject if too risky
        if peak_load > 0.9:
            rejected.append((candidate, "Would cause cognitive overload"))
            continue
        if safety_margin < 0.1:
            rejected.append((candidate, "Insufficient safety margin"))
            continue
        if violations:
            rejected.append((candidate, f"Violates {len(violations)} safety policies"))
            continue

        candidates.append(candidate)

    # Select best candidate
    if not candidates:
        return PlannerResult(
            candidates=[],
            selected=None,
            rejection_reasons={r[0].id: r[1] for r in rejected},
            explanation_facts=PlannerExplanation(
                reasons=["all_candidates_rejected"],
                avoided=[],
                tradeoffs=[],
                confidence=0.0,
            ),
        )

    # Sort by score and pick best
    candidates.sort(key=lambda c: -c.overall_score)
    selected = candidates[0]

    # Generate explanation
    explanation = generate_explanation(selected, hypothesis, rejected)

    return PlannerResult(
        candidates=candidates,
        selected=selected,
        rejection_reasons={r[0].id: r[1] for r in rejected},
        explanation_facts=explanation,
    )
