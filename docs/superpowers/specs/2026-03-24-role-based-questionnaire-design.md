# Role-Based Adaptive Questionnaire with Bayesian Learning

**Date:** 2026-03-24
**Status:** Approved
**Project:** AI Timebox

---

## Overview

A personality classification system that seeds user profiles based on role, fine-tunes via adaptive questioning, and continuously learns from behavior. The system uses weighted-average belief updating to adapt scheduling parameters in real time, with weekly check-ins targeting the highest-uncertainty parameter.

The questionnaire is not the product — it's the cold start. The learning engine is the product.

**Key distinction:** The belief system operates on 6 *scheduling preferences* (peak_energy, deep_work_tolerance, etc.) that are higher-level than the 7 HumanState *cognitive dimensions* (cognitive_load, energy_level, etc.). Beliefs inform how HumanState parameters are initialized and how the planner selects time slots — they don't replace HumanState.

---

## 1. Role Profiles (Seed Parameters)

Five roles, each providing initial values for six scheduling parameters:

| Parameter | Student | Professional | Freelancer | Manager | Creative |
|-----------|---------|-------------|------------|---------|----------|
| Peak energy window | 10pm-1am | 9am-12pm | 10am-1pm | 8am-11am | 11pm-2am |
| Deep work tolerance | 45 min | 90 min | 60 min | 30 min | 120 min |
| Meeting tolerance | Low (0.3) | Medium (0.5) | Low (0.3) | High (0.8) | Very Low (0.2) |
| Context-switch cost | High (0.7) | Medium (0.5) | Medium (0.5) | Low (0.3) | Very High (0.8) |
| Chaos tolerance | 0.4 | 0.5 | 0.6 | 0.7 | 0.3 |
| Cognitive recovery rate | Fast (0.15/hr) | Medium (0.10/hr) | Medium (0.10/hr) | Fast (0.15/hr) | Slow (0.07/hr) |

**Selection:** First screen of onboarding. Single selection: "What best describes you?" All values are starting points with initial confidence of 0.5.

---

## 2. Adaptive Questionnaire

### 2.1 Core Questions (always asked)

**Q1: "When do you feel sharpest?"**
- Options: Morning / Afternoon / Evening / Late Night
- Maps to: `peak_energy` parameter
- If answer contradicts role default, triggers follow-up

**Q2: "How long can you focus without a break?"**
- Options: Under 30 min / 30-60 min / 1-2 hours / 2+ hours
- Maps to: `deep_work_tolerance` parameter
- If answer contradicts role default, triggers follow-up

**Q3: "What drains you most?"**
- Options: Meetings / Context switching / Unclear tasks / Long focus sessions
- Maps to: highest cognitive cost activity type
- Adjusts `meeting_tolerance`, `context_switch_cost`, or `deep_work_tolerance` accordingly

### 2.2 Adaptive Follow-ups (conditional)

Triggered when core answers conflict with role defaults:

| Conflict | Follow-up |
|----------|-----------|
| Energy peak contradicts role | "Do you have a fixed schedule (classes/office) or flexible hours?" |
| Focus duration unusually high/low for role | "Do you work in one long stretch or multiple short ones?" |
| Chaos tolerance unclear | "When your plan gets disrupted, do you rework it or push through?" |
| Meeting tolerance unclear (Manager/Professional) | "How many meetings is too many in one day?" |

### 2.3 Question Count

- Minimum: 4 (role + 3 core)
- Maximum: 7 (role + 3 core + 3 adaptive)
- Adaptive questions fire when the **conflict score** exceeds 0.3. Conflict score is the normalized absolute difference between the questionnaire answer and the role default: `conflict = abs(answer_encoded - role_default_encoded) / parameter_range`. For example, if a Student (default peak_energy = 22.0) answers "Morning" (encoded as 9.0), conflict = abs(9.0 - 22.0) / 24.0 = 0.54 → triggers follow-up.

### 2.4 Output

Natural-language summary displayed to user:
> "You're set up for late-night deep work in 45-minute sprints, with long breaks between context switches. We'll learn more as you use the app."

No editable profile. No visible labels or classifications.

---

## 3. Behavioral Learning Engine

### 3.1 Belief Model

Each user has 6 parameters, each stored as a belief:

```
UserBelief:
  parameter: enum (peak_energy, deep_work_tolerance, context_switch_cost,
                   chaos_tolerance, meeting_tolerance, recovery_rate)
  belief_value: float     # Current estimate
  confidence: float       # 0.0 - 0.95
  last_updated: timestamp
  evidence_count: int
```

Initial state after questionnaire: belief_value from role defaults + questionnaire adjustments, confidence 0.5.

### 3.2 Behavioral Signals

Four signals the system observes:

| Signal | What it measures | How captured |
|--------|-----------------|--------------|
| Block completion | Did user finish the block? | Mark complete / skip / partial |
| Reschedule direction | When user moves a task, to when? | Compare original vs new time |
| Self-initiated scheduling | When user freely adds a task, what time? | Log chosen slot |
| Energy self-report | User-rated energy level | 1-tap prompt (low/ok/great) at end of deep work blocks |

### 3.3 Numeric Encoding

All belief parameters are stored as floats. Here's how each is encoded:

| Parameter | Encoding | Range | Example |
|-----------|----------|-------|---------|
| `peak_energy` | Hour of day (float, 24h) | 0.0 - 23.99 | 10pm = 22.0, 2pm = 14.0 |
| `deep_work_tolerance` | Minutes | 15.0 - 180.0 | 45 min = 45.0 |
| `context_switch_cost` | 0-1 scale | 0.0 - 1.0 | High = 0.7 |
| `chaos_tolerance` | 0-1 scale | 0.0 - 1.0 | 0.4 |
| `meeting_tolerance` | 0-1 scale | 0.0 - 1.0 | Low = 0.3 |
| `recovery_rate` | Units per hour | 0.03 - 0.20 | Fast = 0.15 |

**Questionnaire answer encodings:**

| Question | Answer → Encoded value |
|----------|----------------------|
| "When do you feel sharpest?" | Morning = 9.0, Afternoon = 14.0, Evening = 20.0, Late Night = 23.0 |
| "How long can you focus?" | Under 30 min = 25.0, 30-60 min = 45.0, 1-2 hours = 90.0, 2+ hours = 150.0 |
| "What drains you most?" | Meetings → meeting_tolerance -= 0.2; Context switching → context_switch_cost += 0.2; Long focus → deep_work_tolerance -= 15.0 |

**Observation encodings (from behavioral signals):**

| Signal | Observation value |
|--------|------------------|
| Block completed at time T | peak_energy observation = T (hour float) |
| Block skipped at time T | peak_energy observation = opposite_of(T): if T < 12 then 20.0, else 10.0 |
| Reschedule from T1 to T2 | peak_energy observation = T2 |
| Block of duration D completed | deep_work_tolerance observation = D (minutes) |
| Block of duration D partially completed | deep_work_tolerance observation = D × 0.5 |
| Energy self-report: Low/OK/Great | Maps to 0.3 / 0.6 / 0.9 as energy observation for current hour |

### 3.4 Update Formula

```
new_belief = (old_belief * old_confidence + observation * signal_weight) / (old_confidence + signal_weight)
new_confidence = min(old_confidence + signal_weight * 0.1, 0.95)
```

**Worked example — peak_energy update:**
- Old belief: 22.0 (10pm), confidence: 0.5
- Observation: User completes block at 14.0 (2pm) → signal_weight = 0.3
- new_belief = (22.0 × 0.5 + 14.0 × 0.3) / (0.5 + 0.3) = (11.0 + 4.2) / 0.8 = 19.0
- new_confidence = min(0.5 + 0.3 × 0.1, 0.95) = 0.53
- Result: Peak energy shifts from 22.0 → 19.0 (7pm), confidence 0.53

Note: For `peak_energy`, the belief value wraps around 24h. When `abs(old_belief - observation) > 12`, use modular arithmetic: treat 23.0 and 1.0 as 2 hours apart, not 22.

Signal weights:
- Block completion/skip: **0.3**
- User-initiated reschedule: **0.4** (strongest — deliberate action)
- Self-scheduled time choice: **0.2**
- Energy self-report: **0.5** (direct input, highest trust)

### 3.5 Confidence Mechanics

- **Cap:** 0.95 — system never reaches full certainty, always stays open to change
- **Decay:** Confidence decays by 0.01/day if no new evidence arrives for a parameter
- **Floor:** Confidence never drops below 0.2 — prevents wild swings from single observations after long inactivity

### 3.6 Parameter-Signal Mapping

| Parameter | Updated by |
|-----------|-----------|
| Peak energy window | Completion rates by time-of-day, reschedule targets, self-scheduling times |
| Deep work tolerance | Completion rates by block duration, partial completions |
| Context-switch cost | Performance after back-to-back vs buffered blocks |
| Chaos tolerance | Response to schedule disruptions (reschedule vs push through) |
| Meeting tolerance | Completion/skip rates for meeting-adjacent blocks |
| Cognitive recovery rate | Time gap between block end and next user-initiated block start |

### 3.7 Example Adaptation Timeline

Day 1: Student role selected, questionnaire says "sharpest in evening." Peak energy belief = 10pm, confidence 0.5.

Day 3: User completes 2pm block early, skips 10pm block. Afternoon estimate rises, evening drops. Confidence in evening falls to 0.4.

Day 6: User self-schedules a task at 3pm. Afternoon estimate rises further. Confidence toward afternoon reaches 0.6.

Day 10: System schedules most deep work in the afternoon. No question was asked — behavior taught the system.

---

## 4. Weekly Check-in

### 4.1 Trigger

Every Sunday evening (time configurable by user). System selects the parameter with the lowest confidence score.

### 4.2 Question Generation

Each question is contextual — references real data from the past week, not generic phrasing.

| Lowest confidence parameter | Example question |
|----------------------------|-----------------|
| Peak energy | "This week you were most productive around 3pm. Does that feel right?" |
| Deep work tolerance | "We've been giving you 45-min blocks. Too short, too long, or about right?" |
| Context-switch cost | "You had 3 back-to-back switches on Tuesday. How did that feel?" |
| Chaos tolerance | "Your Wednesday got reshuffled. Did that throw you off or was it fine?" |
| Meeting tolerance | "You had 4 meetings Thursday. Was that manageable?" |
| Recovery rate | "After your deep work block Friday, you took a 2-hour break. Was that needed or too long?" |

### 4.3 Rules

- **Single question only.** One per week maximum.
- **Grounded in real data.** Always references specific days/events.
- **Skip if unnecessary.** If all parameters have confidence > 0.8, no check-in. System says: "Looks like we've got a good read on you this week."
- **Optional.** If dismissed, no penalty. Confidence continues natural decay.
- **High signal weight.** Answer receives weight 0.5 (same as energy self-report — direct user input).

---

## 5. Integration with Existing Architecture

### 5.1 New Components

| Component | Purpose | Location |
|-----------|---------|---------|
| `RoleProfile` | Dataclass with role defaults (seed parameters per role) | `backend/app/models/role_profile.py` |
| `UserBelief` | Per-parameter belief + confidence with update logic | `backend/app/models/user_belief.py` |
| `BehavioralTracker` | Observes signals from block completions, reschedules, self-scheduling | `backend/app/services/behavioral_tracker.py` |
| `BeliefUpdater` | Runs the Bayesian update formula, manages confidence decay | `backend/app/services/belief_updater.py` |
| `CheckInGenerator` | Picks lowest-confidence parameter, generates contextual question | `backend/app/services/checkin_generator.py` |

### 5.2 Changes to Existing Components

| Component | Change |
|-----------|--------|
| `questionnaire.py` | Replace with new adaptive questionnaire using role profiles |
| `onboarding_orchestrator.py` | Add role selection as Phase 0, feed into adaptive questionnaire |
| `schedule_generator.py` | Before generating, resolve beliefs → HumanState parameters |
| `planner.py` | Read from resolved beliefs instead of static defaults |
| `ScheduledBlockORM` | Add `status` field: completed / skipped / partial |
| `UserORM` | Add `role` field (enum) |
| `HumanState` | No change — beliefs resolve into HumanState before scheduling |

### 5.3 New Database Table

```
UserBeliefORM:
  - id: UUID (PK)
  - user_id: UUID (FK → users)
  - parameter: Enum (peak_energy, deep_work_tolerance, context_switch_cost,
                     chaos_tolerance, meeting_tolerance, recovery_rate)
  - belief_value: Float
  - confidence: Float (0.0 - 0.95)
  - last_updated: DateTime
  - evidence_count: Integer
```

### 5.4 Data Flow

```
Role Selection
  → Seed Beliefs (5 roles x 6 parameters)
  → Adaptive Questionnaire
  → Fine-tuned Beliefs (confidence 0.5)
  → Daily Usage
  → BehavioralTracker captures signals
  → BeliefUpdater adjusts belief + confidence per parameter
  → Planner reads resolved beliefs → Generates schedule
  → Weekly: CheckInGenerator picks lowest confidence
  → Asks 1 contextual question
  → Updates belief (weight 0.5)
  → Loop continues
```

### 5.5 Belief-to-HumanState Resolution Function

Beliefs are scheduling preferences. HumanState is the real-time cognitive state. Beliefs influence HumanState initialization and planner decisions — they don't replace HumanState fields.

**Resolution (runs before each scheduling call):**

```python
def resolve_beliefs_to_scheduling_context(beliefs: dict[str, UserBelief], current_time: datetime) -> SchedulingContext:
    """Convert beliefs into parameters the planner uses."""
    return SchedulingContext(
        # peak_energy belief → planner's preferred time window for deep work
        peak_energy_start=beliefs['peak_energy'].belief_value - 1.5,  # 1.5 hours before peak
        peak_energy_end=beliefs['peak_energy'].belief_value + 1.5,    # 1.5 hours after peak

        # deep_work_tolerance → max block duration the planner will create
        max_block_duration_minutes=beliefs['deep_work_tolerance'].belief_value,

        # context_switch_cost → min buffer between different-context blocks
        min_buffer_minutes=beliefs['context_switch_cost'].belief_value * 30,  # 0.7 → 21 min buffer

        # chaos_tolerance → HumanState.chaos_tolerance (direct map, same scale)
        initial_chaos_tolerance=beliefs['chaos_tolerance'].belief_value,

        # meeting_tolerance → max consecutive meetings before forced break
        max_consecutive_meetings=round(beliefs['meeting_tolerance'].belief_value * 5),  # 0.8 → 4 meetings

        # recovery_rate → HumanState cognitive recovery rate (direct map)
        cognitive_recovery_rate=beliefs['recovery_rate'].belief_value,
    )
```

**What stays on HumanState:** `cognitive_load`, `emotional_load`, `energy_level`, `context_residue`, `confidence`, `fragility` remain real-time values computed from task impacts and decay. Beliefs don't overwrite these — they inform the planner's *decisions* about what to schedule when.

### 5.6 Safety Policy Migration

The existing `questionnaire.py` creates initial `SafetyPolicy` objects from onboarding answers. The new system preserves this:

- **Role profiles include default safety policies.** Each role has 2-3 preset policies (e.g., Student: "no deep work blocks after 2am", Manager: "mandatory break after 3 consecutive meetings").
- **Adaptive questionnaire may add policies.** If a user reports high sensitivity to context switching, a policy is created: "insert 15-min buffer after every meeting."
- **The existing `create_default_policies()` function is refactored** to accept a `RoleProfile` + questionnaire answers instead of raw answer dict.
- **`notification_preference`** (from the old questionnaire) is preserved as a 7th belief parameter: `guidance_level`. Encoded as 0-1 scale (minimal=0.2, balanced=0.5, involved=0.8). This controls how aggressively the system prompts for energy self-reports and surfaces explanations. Default per role: Student=0.5, Professional=0.5, Freelancer=0.3, Manager=0.3, Creative=0.5.

### 5.7 Block Status Lifecycle

The `ScheduledBlockORM.status` field uses a String enum with these values:

| Status | Meaning | Default? |
|--------|---------|----------|
| `scheduled` | Block created, not yet reached | Yes (default) |
| `in_progress` | Current time is within block window | |
| `completed` | User marked done or block time passed + completion inferred | |
| `skipped` | User explicitly skipped or block time passed with no activity | |
| `partial` | User started but ended early | |
| `rescheduled` | User moved this block to a different time | |

Transition: `scheduled` → `in_progress` → `completed`/`skipped`/`partial`. `rescheduled` can happen from `scheduled` or `in_progress`.

### 5.8 BehavioralTracker Hook Points

Where tracking code is inserted in existing files:

| Signal | Hook location | Trigger |
|--------|--------------|---------|
| Block completion | `backend/app/api/adjust.py` — new `PATCH /api/blocks/{id}/status` endpoint | User marks block done/skipped/partial |
| Block auto-completion | `backend/app/services/schedule_generator.py` — end-of-block check | Block end time passes |
| Reschedule | `backend/app/api/adjust.py` — existing adjustment endpoint | User moves a block, log original + new time |
| Self-scheduling | `backend/app/api/intents.py` — after intent resolution creates a block | User adds a new task freely |
| Energy self-report | New `POST /api/self-report/energy` endpoint | Frontend prompts after deep work blocks |

### 5.9 Weekly Check-in Scheduling

**Mechanism:** Client-side timer, not server cron.

- Frontend stores the user's preferred check-in day/time (default: Sunday 7pm)
- When the app is opened and the check-in is due (current time > last_checkin + 7 days), frontend calls `GET /api/checkin/next`
- Backend picks the lowest-confidence parameter, generates the question, returns it
- Frontend displays the card overlay
- User answer goes to `POST /api/checkin/answer`
- If app isn't opened on Sunday, check-in triggers on next app open

This avoids needing server-side cron or push notifications for v1.

### 5.10 API Endpoints (New)

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| POST | `/api/onboarding/role` | Submit role selection | `{ role: "student" }` | `{ beliefs: [...], next_question: {...} }` |
| POST | `/api/onboarding/questionnaire` | Submit questionnaire answer | `{ question_id: str, answer: str }` | `{ next_question: {...} \| null, summary: str \| null }` |
| GET | `/api/beliefs` | Get current beliefs for user | — | `{ beliefs: [{ parameter, value, confidence }] }` |
| PATCH | `/api/blocks/{id}/status` | Update block status | `{ status: "completed" }` | `{ updated: true }` |
| POST | `/api/self-report/energy` | Submit energy self-report | `{ level: "low"\|"ok"\|"great", block_id: uuid }` | `{ recorded: true }` |
| GET | `/api/checkin/next` | Get weekly check-in question | — | `{ question: str, options: [...], parameter: str } \| { skip: true, message: str }` |
| POST | `/api/checkin/answer` | Submit check-in answer | `{ parameter: str, answer: str }` | `{ updated: true }` |

### 5.11 UserProfile Relationship

The existing `UserProfile` dataclass (wake_time, sleep_time, work_start, work_end, peak_energy_start, peak_energy_end) is **kept** for time-of-day scheduling boundaries. The `peak_energy_start` and `peak_energy_end` fields are initialized from the `peak_energy` belief (belief_value ± 1.5 hours) and updated whenever the belief updates. UserProfile holds resolved scheduling windows; UserBelief holds the learning state.

### 5.12 Untouched Components

- Safety policies — still act as guardrails regardless of beliefs (initial policies now generated from role profile)
- Intent parsing (IHF 2.0) — unchanged
- Timeline/undo system — unchanged
- Question policy (VOI/COI) — unchanged

---

## 6. Frontend Changes

### 6.1 Onboarding Flow (modified)

1. **Phase 0 (new): Role Selection** — 5 cards, single pick
2. **Phase 1: Adaptive Questionnaire** — 3 core + 0-3 follow-ups, one per screen
3. **Phase 2: Summary** — Natural language summary of profile
4. **Phase 3: Time inputs** — Wake/sleep/work times (existing)
5. **Phase 4: Theme + Chat** — Weekly focus + task extraction (existing)

### 6.2 Weekly Check-in UI

- Card overlay on Sunday evening
- Single question with 2-3 tap options
- Dismiss button (no penalty)
- "We've got a good read on you" message when all confidence > 0.8

### 6.3 Energy Self-Report

- 1-tap prompt after deep work blocks complete
- Three options: Low / OK / Great
- Non-blocking — auto-dismisses after 10 seconds if ignored

---

## 7. Edge Cases

| Scenario | Handling |
|----------|---------|
| User picks wrong role | Behavioral learning corrects within 1-2 weeks. Adaptive questions catch major mismatches immediately. |
| User is hybrid (student + freelancer) | Single role selection. Adaptive questions + behavioral learning capture the nuances the role missed. |
| User behavior changes (exam season, vacation) | Confidence decay ensures system stays open. Weekly check-in detects shifts. |
| User never completes blocks (no signal) | Skips are signals too — system learns from what's avoided, not just what's completed. |
| All confidence scores plateau at ~0.6 | Inconsistent behavior. System keeps asking weekly, schedules conservatively using safety policies. |
| User dismisses every check-in | Confidence decays slowly. System relies on behavioral signals only. Still adapts, just slower. |
| User closes app after a block (no next block observed) | Recovery rate gets no signal — confidence decays naturally. Only measured when user starts a new block within 4 hours of completing one. |
| peak_energy belief oscillates (morning one week, evening next) | Confidence stays low (~0.4-0.5), system hedges by spreading deep work across both windows. |
