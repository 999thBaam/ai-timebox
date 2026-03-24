# Role-Based Adaptive Questionnaire with Bayesian Learning

**Date:** 2026-03-24
**Status:** Approved
**Project:** AI Timebox

---

## Overview

A personality classification system that seeds user profiles based on role, fine-tunes via adaptive questioning, and continuously learns from behavior. The system uses Bayesian-style belief updating to adapt scheduling parameters in real time, with weekly check-ins targeting the highest-uncertainty parameter.

The questionnaire is not the product — it's the cold start. The learning engine is the product.

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
- Adaptive questions only fire when conflict confidence exceeds 0.3 (i.e., the core answer meaningfully diverges from role default)

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

### 3.3 Update Formula

```
new_belief = (old_belief * old_confidence + observation * signal_weight) / (old_confidence + signal_weight)
new_confidence = min(old_confidence + signal_weight * 0.1, 0.95)
```

Signal weights:
- Block completion/skip: **0.3**
- User-initiated reschedule: **0.4** (strongest — deliberate action)
- Self-scheduled time choice: **0.2**
- Energy self-report: **0.5** (direct input, highest trust)

### 3.4 Confidence Mechanics

- **Cap:** 0.95 — system never reaches full certainty, always stays open to change
- **Decay:** Confidence decays by 0.01/day if no new evidence arrives for a parameter
- **Floor:** Confidence never drops below 0.2 — prevents wild swings from single observations after long inactivity

### 3.5 Parameter-Signal Mapping

| Parameter | Updated by |
|-----------|-----------|
| Peak energy window | Completion rates by time-of-day, reschedule targets, self-scheduling times |
| Deep work tolerance | Completion rates by block duration, partial completions |
| Context-switch cost | Performance after back-to-back vs buffered blocks |
| Chaos tolerance | Response to schedule disruptions (reschedule vs push through) |
| Meeting tolerance | Completion/skip rates for meeting-adjacent blocks |
| Cognitive recovery rate | Time gap between block end and next user-initiated block start |

### 3.6 Example Adaptation Timeline

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

### 5.5 Untouched Components

- Safety policies — still act as guardrails regardless of beliefs
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
