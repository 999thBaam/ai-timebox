# AI Timebox iOS App — Design Spec

## Context

The existing web app (Next.js + FastAPI) has a 7-phase onboarding with abstract personality questions that users can't accurately answer. Research shows 75% of users churn in the first week if they don't see immediate value. The current approach frontloads self-assessment before delivering any benefit.

This spec redesigns AI Timebox as a native iOS app (Flutter) with a fundamentally different philosophy: **plan your day IS the onboarding.** No questionnaire. Instant value on day 1. The Bayesian belief system learns everything from behavior.

The first user is the developer himself — a startup founder, part-time teacher (3 days/week, schedule changes weekly), who wants to build health habits gradually and has variable social/errand commitments.

## Platform & Stack

- **Framework:** Flutter (Dart)
- **Target:** iOS (iPhone)
- **Backend:** None — fully local, on-device
- **Database:** SQLite via `sqflite`
- **LLM:** Claude API (Sonnet) for schedule generation, task understanding, and insights
- **Voice:** iOS speech-to-text via `speech_to_text` package
- **Offline fallback:** Rule-based scheduler when no network available
- **API key:** Stored in iOS Keychain via `flutter_secure_storage`. User enters their own Claude API key in settings on first use. Not bundled in the binary.
- **DB migrations:** Use `sqflite` `onUpgrade` callback with version numbers for schema changes.

## Core Philosophy

1. **Day 1 value** — Open the app, dump tasks, get a smart schedule in 30 seconds
2. **No self-assessment** — The system learns who you are from how you use it
3. **Compassionate** — No guilt for undone tasks, no punishment for skipped health
4. **Whole life** — Handles work, health, errands, social — not just productivity
5. **Gradual habits** — Health suggestions start small, build over weeks

---

## Data Model

### Task
| Field | Type | Description |
|-------|------|-------------|
| id | String (UUID) | Unique identifier |
| title | String | Task description |
| pillar | Enum: work/health/errand/social | Auto-detected by LLM from task text |
| estimated_minutes | int | LLM-estimated duration |
| task_type | Enum: deep_focus/quick/outing/call | LLM-classified type |
| status | Enum: pending/done/moved/dropped | Current state. `moved` = rolled to another day, `dropped` = user chose "let it go" at any escalation level. Dropped tasks go to an archived list and can be revived. |
| created_at | DateTime | When created |
| scheduled_date | Date | Which day it's on |
| scheduled_time | Time? | Assigned time slot (null if unscheduled) |
| times_moved | int | How many times this task has rolled over |

### DayPlan
| Field | Type | Description |
|-------|------|-------------|
| id | String (UUID) | Unique identifier |
| date | Date | The day |
| day_type | Enum: teaching/free | From WeekConfig. No separate "social" type — social activities are just tasks with pillar=social on any day. |
| wake_time | Time | User's wake time |
| sleep_time | Time | User's sleep time |
| schedule_json | String | LLM-generated schedule as JSON array of ScheduleSlot objects (see LLM Output Schemas) |
| insight | String? | LLM-generated daily insight |

### WeekConfig
| Field | Type | Description |
|-------|------|-------------|
| id | String (UUID) | Unique identifier |
| week_start_date | Date | Monday of the week |
| teaching_days | List<int> | Day indices (0=Mon, 6=Sun) |
| wake_time | Time | Default wake time |
| sleep_time | Time | Default sleep time |

### Belief
| Field | Type | Description |
|-------|------|-------------|
| parameter | Enum (6 values) | PEAK_ENERGY, DEEP_WORK_TOLERANCE, CONTEXT_SWITCH_COST, CHAOS_TOLERANCE, MEETING_TOLERANCE, RECOVERY_RATE |
| value | double | Current belief value |
| confidence | double | 0.0–0.95 |
| last_updated | DateTime | When last updated |
| evidence_count | int | Number of observations |

### HealthLog
| Field | Type | Description |
|-------|------|-------------|
| id | String (UUID) | Unique identifier |
| date | Date | When it happened |
| activity_type | String | walk/gym/etc |
| duration_minutes | int | How long |
| was_suggested | bool | Did the app suggest it? |

### DayReview
| Field | Type | Description |
|-------|------|-------------|
| id | String (UUID) | Unique identifier |
| date | Date | The day |
| completed_count | int | Tasks completed |
| total_count | int | Total tasks planned |
| streak_day | int | Consecutive days of app usage (opened and planned or reviewed). Resets to 0 if a day is fully skipped. |

---

## LLM Integration

The LLM (Claude Sonnet via API) handles three jobs:

### Job 1: Task Understanding
Input: Raw task text (typed or spoken). **Batched** — all tasks sent in one call to minimize API usage.

Output schema (per task):
```json
{
  "title": "Work on login screen",
  "pillar": "work",
  "estimated_minutes": 90,
  "task_type": "deep_focus"
}
```
Valid `pillar` values: `work`, `health`, `errand`, `social`
Valid `task_type` values: `deep_focus`, `quick`, `outing`, `call`

### Job 2: Schedule Generation
Input (structured prompt):
- Today's tasks with parsed metadata from Job 1
- Day type (teaching/free)
- Wake/sleep times
- All 6 beliefs with confidence levels (included in LLM prompt as context)
- Health habit history (last 7 days of HealthLog)
- Health progression phase (silent/gentle/pattern/habit/adapted)
- Undone tasks rolled from yesterday

Output schema — `ScheduleSlot` array:
```json
{
  "slots": [
    {
      "task_id": "uuid-or-null",
      "slot_type": "task",
      "start_time": "09:00",
      "end_time": "11:00",
      "title": "Work on login screen",
      "pillar": "work"
    },
    {
      "task_id": null,
      "slot_type": "buffer",
      "start_time": "11:00",
      "end_time": "11:15",
      "title": "Buffer",
      "pillar": null
    },
    {
      "task_id": null,
      "slot_type": "health_nudge",
      "start_time": "12:30",
      "end_time": "12:50",
      "title": "Go for a short walk?",
      "pillar": "health"
    },
    {
      "task_id": null,
      "slot_type": "open",
      "start_time": "15:00",
      "end_time": "17:00",
      "title": "Open time",
      "pillar": null
    }
  ],
  "insight": "You have a solid 2-hour block for deep work this morning."
}
```
Valid `slot_type` values: `task`, `buffer`, `health_nudge`, `open`

### Job 3: Insights & Nudges
Triggered at end of day and weekly. Combined into the evening review API call.

Input: Week's worth of DayReviews, HealthLogs, task completion patterns, belief snapshots

Output schema:
```json
{
  "daily_insight": "You finished both deep work tasks before noon. That's becoming a pattern.",
  "health_insight": "3 walks this week — your best yet.",
  "undone_prompts": [
    {
      "task_id": "uuid",
      "message": "Haircut has slipped 3 days. Timing isn't right.",
      "suggestion": "lock_in"
    }
  ]
}
```
Valid `suggestion` values: `move_tomorrow`, `pick_day`, `lock_in`

### Error Handling
- If LLM returns malformed JSON: retry once. If second attempt fails, fall back to rule-based scheduler.
- If API is unreachable: use offline fallback immediately, no retry loop.
- All LLM calls use `response_format: json` (Claude structured output) to minimize parse errors.

### Cost
Task understanding is batched (1 call for all tasks). Schedule generation is 1 call. Evening review is 1 call. Total: ~3 API calls/day. Estimated $0.10-0.20/day with Claude Sonnet.

### Offline Fallback
Rule-based scheduler when no network:
1. Sort tasks: deep_focus first, then quick, then outing
2. Place deep_focus tasks starting at peak_energy belief hour
3. Place quick tasks in gaps
4. Add buffers based on context_switch_cost belief (high=15min, low=5min)
5. Place outings in afternoon by default
6. No health nudges or insights generated offline
7. Show "Offline mode — schedule may improve when connected" banner

---

## Belief System (Ported from Python to Dart)

### 6 Parameters
| Parameter | Range | Initial Value | What it tracks |
|-----------|-------|--------------|---------------|
| PEAK_ENERGY | 0–24 (hour) | 10.0 | When they do best work |
| DEEP_WORK_TOLERANCE | 15–180 (min) | 60.0 | How long they can focus |
| CONTEXT_SWITCH_COST | 0–1 | 0.5 | How much switching hurts |
| CHAOS_TOLERANCE | 0–1 | 0.4 | How they handle disruptions |
| MEETING_TOLERANCE | 0–1 | 0.5 | Meeting capacity |
| RECOVERY_RATE | 0.03–0.20 | 0.10 | Recovery speed (units/hour, matching existing Python formula) |

GUIDANCE_LEVEL is removed — it had no behavioral signal to update it and no impact on scheduling. If needed later, it can be re-added when there's a clear update mechanism.

### Initial State
All beliefs start at the values above with confidence **0.3** (deliberately lower than the existing Python code's 0.5, so the system learns faster from early interactions). No role selection screen.

### Update Formula (same as existing Python)
```
new_belief = (old_belief × confidence + observation × signal_weight) / (confidence + signal_weight)
new_confidence = min(confidence + signal_weight × 0.1, 0.95)
```

### Signal Weights
| Signal | Weight | Source |
|--------|--------|--------|
| Energy self-report | 0.5 | User says "great/ok/low" |
| Reschedule | 0.4 | User moves a task to different time |
| Block completion | 0.3 | User marks task done |
| Self-scheduled | 0.2 | User creates a block at a specific time |

### Confidence Mechanics
- Cap: 0.95 (never fully certain)
- Floor: 0.2 (never fully lost)
- Decay: 0.01/day if not updated
- No explicit check-in screens in V1. The LLM uses low-confidence beliefs to generate better prompts in the schedule (e.g., trying different time slots to gather data).

### Behavioral Learning
| User action | What system learns |
|-------------|-------------------|
| Completes task at 2pm | Peak energy shifts toward 2pm |
| Skips 9am task repeatedly | "Morning isn't their time" |
| Skips after meetings | Low meeting tolerance, needs buffer |
| Completes short tasks, skips long | Deep work tolerance lower than estimated |
| Reschedules to evening | Peak energy shifts toward evening |
| Does back-to-back tasks | Low context-switch cost |

---

## Health Habit System

### Progression Phases
| Phase | Timeframe | Behavior |
|-------|-----------|----------|
| Silent | Days 1–3 | No suggestions. Learning schedule. |
| Gentle nudge | Days 4–7 | One suggestion/day in 20+ min gaps: "Free time — go for a short walk?" |
| Pattern forming | Week 2–3 | If 2+ nudges accepted: slightly more frequent suggestions |
| Habit building | Week 4+ | Gradual increase: longer duration, new activities suggested |
| Adapted | Month 2+ | Fully learned: knows which days, times, durations work |

### Skip Handling
- No guilt messaging
- Quietly retries next available gap
- After full week of skips: dials back to gentle nudge phase
- Never punishes, only reinforces success

### Tracking
- HealthLog records every activity (suggested or self-initiated)
- Belief system updates RECOVERY_RATE based on activity patterns
- Streak shown in end-of-day review (small, not center stage)

---

## Undone Task Handling

### Escalation Ladder
| Times undone | Response |
|-------------|----------|
| 1 | "Didn't happen. That's okay." → Move to tomorrow / Let it go |
| 2 | "Slipped twice. Still want to do it?" → Pick a specific day / Let it go |
| 3 | "Been on your list 3 days. Timing isn't right." → Lock it in (LLM picks best slot) / Archive |

### Archive
- Removed from daily view
- Accessible in archived list
- No reminders, no guilt
- Can be revived anytime

---

## First Launch Flow

### Step 1: Tap Teaching Days (~10 seconds)
Week grid showing Mon–Sun. Tap days you're teaching this week. Text: "You can update this every week."

### Step 2: Wake & Sleep (~5 seconds)
Scroll pickers. Defaults: 7:00 AM / 11:00 PM.

### Done → "What's on your plate today?"
Straight to the daily planner. Total setup: under 30 seconds.

### Weekly Update
When teaching schedule changes: tap "Update days" on week view → same grid → tap/untap → done in 5 seconds.

Tasks on days that change from free→teaching get flagged: "Wednesday is now a teaching day. Move these tasks?"

---

## Screens

### 1. Daily Screen (Main)
- Greeting: "Good morning." + day type
- Task list with add input (text + mic)
- "Plan my day" button → shows loading state while LLM responds (5-15 seconds typical)
- After planning: timeline view with color-coded blocks
- Health nudge appears in gaps (dashed border, gentle green)
- Open time blocks shown faded
- **Energy check:** When user marks a deep work task as done, a subtle 1-tap prompt appears: "How was that? 🔋" → Low / OK / Great (auto-dismisses after 10 seconds). Updates PEAK_ENERGY belief.

### 2. Week Screen
- Day pills row (teaching=indigo, free=default, social=amber, today=highlighted)
- Tap day to see its tasks
- "Update days" link
- Weekly progress bar (done/moved/upcoming)

### 3. Review Screen (End of Day)
- Checklist of today's tasks (done=checked, undone=open)
- Per-undone-task: compassionate options (move/drop)
- Stats row: completed count, health activity, streak
- LLM insight at bottom

### 4. Setup Screen (First Launch + Weekly Update)
- Week grid with tappable day pills
- Wake/sleep time pickers

---

## Visual Design

Inspired by Things 3 (generous spacing, typography), Structured (clean timeline), Apple Liquid Glass (frosted glass cards).

- **Theme:** Dark mode primary (slate-950 background)
- **Cards:** Frosted glass effect — `rgba(255,255,255,0.04)` background, subtle border
- **Task blocks:** Color-coded by pillar — indigo (work), emerald (health), amber (errand), rose (social)
- **Typography:** Inter or SF Pro. Large greeting (22px bold), section titles (11px uppercase), task text (13.5px regular)
- **Spacing:** Generous — Things 3 style relaxed spacing throughout
- **Animations:** Smooth, purposeful transitions. Block completion feels satisfying.

---

## Notifications

- **Morning:** "Ready to plan your day?" (configurable time, default 8am)
- **End of day:** "How did today go?" (configurable, default 9pm)
- **Max 2/day.** No nagging. Both dismissable.

---

## App Architecture

```
lib/
├── main.dart
├── models/          # Data classes
│   ├── task.dart
│   ├── day_plan.dart
│   ├── week_config.dart
│   ├── belief.dart
│   ├── health_log.dart
│   └── day_review.dart
├── services/        # Business logic
│   ├── llm_service.dart          # Claude API calls
│   ├── scheduler_service.dart    # Orchestrates plan generation
│   ├── belief_engine.dart        # Bayesian updates (ported from Python)
│   ├── health_tracker.dart       # Habit progression
│   ├── task_parser.dart          # LLM task understanding
│   ├── insight_generator.dart    # LLM insights
│   └── speech_service.dart       # iOS speech-to-text
├── screens/         # Full-page views
│   ├── daily_screen.dart
│   ├── week_screen.dart
│   ├── review_screen.dart
│   └── setup_screen.dart
├── widgets/         # Reusable components
│   ├── task_input.dart
│   ├── timeline_block.dart
│   ├── health_nudge.dart
│   ├── day_pill.dart
│   └── task_check_item.dart
└── storage/
    └── local_db.dart             # SQLite
```

### Dependencies
- `sqflite` — local database
- `speech_to_text` — voice input (requires microphone permission; if denied, mic button hidden, text-only mode)
- `http` — Claude API calls
- `flutter_local_notifications` — reminders
- `shared_preferences` — settings
- `flutter_secure_storage` — API key in iOS Keychain

---

## Verification

### Manual Testing (Developer = First User)
1. First launch: setup completes in < 30 seconds
2. Add 3 tasks → tap "Plan my day" → loading state shown → schedule generated in 5-15 seconds
3. Voice input captures task correctly
4. End of day: mark 2 done, 1 undone → compassionate options shown
5. Move undone task → appears tomorrow
6. After 4 days: health suggestion appears in a gap
7. Accept walk → HealthLog recorded, streak increments
8. Skip walk → no guilt, suggestion reappears next gap
9. Update teaching days → tasks on changed days get flagged
10. Week view shows correct day types and task counts
11. After 1 week: beliefs have shifted from defaults based on actual behavior
12. Offline: schedule still generates via rule-based fallback

### Unit Tests
- Belief engine: update formula, confidence decay, wrapping for peak energy
- Task status transitions: pending → done/moved/dropped/archived
- Health progression: phase transitions based on acceptance rate
- Undone task escalation: 1x → 2x → 3x behavior
