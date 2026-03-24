# Role-Based Adaptive Questionnaire Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add role-based personality classification with adaptive questionnaire and Bayesian behavioral learning to AI Timebox.

**Architecture:** New belief system (7 parameters with confidence scores) sits between user input and the planner. Role profiles seed initial beliefs, adaptive questionnaire fine-tunes them, behavioral tracking continuously updates them, and weekly check-ins target the least confident parameter. Beliefs resolve into a SchedulingContext that the existing planner consumes.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic 2.5, pytest, Next.js 16, React 19, TypeScript

**Spec:** `docs/superpowers/specs/2026-03-24-role-based-questionnaire-design.md`

---

## File Structure

### New Files (Backend Models)
- `backend/app/models/role_profile.py` — RoleProfile dataclass + 5 role definitions + BeliefParameter enum
- `backend/app/models/user_belief.py` — UserBelief dataclass with update logic
- `backend/app/models/scheduling_context.py` — SchedulingContext dataclass + resolve function

### New Files (Backend Services)
- `backend/app/services/adaptive_questionnaire.py` — Adaptive question engine (replaces questionnaire.py)
- `backend/app/services/belief_updater.py` — Weighted-average belief update formula
- `backend/app/services/behavioral_tracker.py` — Signal observation + routing to belief updater
- `backend/app/services/checkin_generator.py` — Weekly check-in question generation

### New Files (Backend API)
- `backend/app/api/beliefs.py` — GET /api/beliefs endpoint
- `backend/app/api/blocks.py` — PATCH /api/blocks/{id}/status endpoint
- `backend/app/api/self_report.py` — POST /api/self-report/energy endpoint
- `backend/app/api/checkin.py` — GET /api/checkin/next + POST /api/checkin/answer

### New Files (Tests)
- `backend/tests/__init__.py`
- `backend/tests/test_role_profile.py`
- `backend/tests/test_user_belief.py`
- `backend/tests/test_belief_updater.py`
- `backend/tests/test_adaptive_questionnaire.py`
- `backend/tests/test_behavioral_tracker.py`
- `backend/tests/test_checkin_generator.py`
- `backend/tests/test_scheduling_context.py`

### New Files (Frontend)
- `frontend/src/components/RoleSelector.tsx` — Role selection cards
- `frontend/src/components/RoleSelector.module.css`
- `frontend/src/components/AdaptiveQuestion.tsx` — Single question display
- `frontend/src/components/AdaptiveQuestion.module.css`
- `frontend/src/components/ProfileSummary.tsx` — Natural language summary
- `frontend/src/components/ProfileSummary.module.css`
- `frontend/src/components/CheckInCard.tsx` — Weekly check-in overlay
- `frontend/src/components/CheckInCard.module.css`
- `frontend/src/components/EnergyReport.tsx` — Post-block energy prompt
- `frontend/src/components/EnergyReport.module.css`

### Modified Files
- `backend/app/db/models.py:17-93` — Add UserBeliefORM, modify UserORM + ScheduledBlockORM
- `backend/app/api/onboarding.py:1-292` — Replace questionnaire endpoints with role + adaptive flow
- `backend/app/api/intents.py:147-261` — Add behavioral tracking hook after block creation
- `backend/app/api/adjust.py:1-91` — Add tracking hook on reschedule
- `backend/app/services/schedule_generator.py:69-200` — Read from SchedulingContext
- `backend/app/services/planner.py:374-508` — Read from SchedulingContext
- `backend/app/main.py` — Register new API routers
- `frontend/src/app/onboarding/page.tsx:1-294` — Add role + questionnaire phases
- `frontend/src/lib/api.ts` — Add new API client functions
- `frontend/src/app/page.tsx` — Add check-in + energy report components

---

## Task 1: BeliefParameter Enum + RoleProfile Model

**Files:**
- Create: `backend/app/models/role_profile.py`
- Test: `backend/tests/test_role_profile.py`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: Create test directory and init**

```bash
mkdir -p "/Users/amitbagra/Desktop/AI timeboxing/backend/tests"
touch "/Users/amitbagra/Desktop/AI timeboxing/backend/tests/__init__.py"
```

- [ ] **Step 2: Write failing tests for RoleProfile**

```python
# backend/tests/test_role_profile.py
from app.models.role_profile import BeliefParameter, RoleType, RoleProfile, get_role_profile


def test_belief_parameter_has_all_seven():
    assert len(BeliefParameter) == 7
    assert BeliefParameter.PEAK_ENERGY in BeliefParameter
    assert BeliefParameter.GUIDANCE_LEVEL in BeliefParameter


def test_role_type_has_five_roles():
    assert len(RoleType) == 5
    names = {r.value for r in RoleType}
    assert names == {"student", "professional", "freelancer", "manager", "creative"}


def test_get_role_profile_student():
    profile = get_role_profile(RoleType.STUDENT)
    assert profile.role == RoleType.STUDENT
    assert profile.defaults[BeliefParameter.PEAK_ENERGY] == 22.0
    assert profile.defaults[BeliefParameter.DEEP_WORK_TOLERANCE] == 45.0
    assert profile.defaults[BeliefParameter.MEETING_TOLERANCE] == 0.3
    assert profile.defaults[BeliefParameter.CONTEXT_SWITCH_COST] == 0.7
    assert profile.defaults[BeliefParameter.CHAOS_TOLERANCE] == 0.4
    assert profile.defaults[BeliefParameter.RECOVERY_RATE] == 0.15
    assert profile.defaults[BeliefParameter.GUIDANCE_LEVEL] == 0.5


def test_get_role_profile_manager():
    profile = get_role_profile(RoleType.MANAGER)
    assert profile.defaults[BeliefParameter.PEAK_ENERGY] == 9.5
    assert profile.defaults[BeliefParameter.MEETING_TOLERANCE] == 0.8
    assert profile.defaults[BeliefParameter.CONTEXT_SWITCH_COST] == 0.3
    assert profile.defaults[BeliefParameter.CHAOS_TOLERANCE] == 0.7


def test_get_role_profile_creative():
    profile = get_role_profile(RoleType.CREATIVE)
    assert profile.defaults[BeliefParameter.PEAK_ENERGY] == 23.5
    assert profile.defaults[BeliefParameter.DEEP_WORK_TOLERANCE] == 120.0
    assert profile.defaults[BeliefParameter.CONTEXT_SWITCH_COST] == 0.8


def test_role_profile_has_default_policies():
    profile = get_role_profile(RoleType.STUDENT)
    assert len(profile.default_policies) >= 2
    # Student should have a late-night cutoff policy
    policy_descriptions = [p["description"] for p in profile.default_policies]
    assert any("2am" in d or "late" in d.lower() for d in policy_descriptions)


def test_all_roles_have_all_parameters():
    for role in RoleType:
        profile = get_role_profile(role)
        for param in BeliefParameter:
            assert param in profile.defaults, f"{role.value} missing {param.value}"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/test_role_profile.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.role_profile'`

- [ ] **Step 4: Implement RoleProfile**

```python
# backend/app/models/role_profile.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BeliefParameter(str, Enum):
    PEAK_ENERGY = "peak_energy"
    DEEP_WORK_TOLERANCE = "deep_work_tolerance"
    CONTEXT_SWITCH_COST = "context_switch_cost"
    CHAOS_TOLERANCE = "chaos_tolerance"
    MEETING_TOLERANCE = "meeting_tolerance"
    RECOVERY_RATE = "recovery_rate"
    GUIDANCE_LEVEL = "guidance_level"


class RoleType(str, Enum):
    STUDENT = "student"
    PROFESSIONAL = "professional"
    FREELANCER = "freelancer"
    MANAGER = "manager"
    CREATIVE = "creative"


@dataclass(frozen=True)
class RoleProfile:
    role: RoleType
    defaults: dict[BeliefParameter, float]
    default_policies: list[dict[str, str]] = field(default_factory=list)


_ROLE_PROFILES: dict[RoleType, RoleProfile] = {
    RoleType.STUDENT: RoleProfile(
        role=RoleType.STUDENT,
        defaults={
            BeliefParameter.PEAK_ENERGY: 22.0,
            BeliefParameter.DEEP_WORK_TOLERANCE: 45.0,
            BeliefParameter.MEETING_TOLERANCE: 0.3,
            BeliefParameter.CONTEXT_SWITCH_COST: 0.7,
            BeliefParameter.CHAOS_TOLERANCE: 0.4,
            BeliefParameter.RECOVERY_RATE: 0.15,
            BeliefParameter.GUIDANCE_LEVEL: 0.5,
        },
        default_policies=[
            {"description": "No deep work blocks after 2am", "condition": "time > 02:00 AND activity = DEEP_WORK", "action": "block"},
            {"description": "Break after 2 consecutive focus blocks", "condition": "consecutive_deep_work >= 2", "action": "insert_break"},
        ],
    ),
    RoleType.PROFESSIONAL: RoleProfile(
        role=RoleType.PROFESSIONAL,
        defaults={
            BeliefParameter.PEAK_ENERGY: 10.5,
            BeliefParameter.DEEP_WORK_TOLERANCE: 90.0,
            BeliefParameter.MEETING_TOLERANCE: 0.5,
            BeliefParameter.CONTEXT_SWITCH_COST: 0.5,
            BeliefParameter.CHAOS_TOLERANCE: 0.5,
            BeliefParameter.RECOVERY_RATE: 0.10,
            BeliefParameter.GUIDANCE_LEVEL: 0.5,
        },
        default_policies=[
            {"description": "Buffer after meetings", "condition": "previous_activity = MEETING", "action": "insert_buffer_10min"},
            {"description": "No deep work after 8pm", "condition": "time > 20:00 AND activity = DEEP_WORK", "action": "block"},
        ],
    ),
    RoleType.FREELANCER: RoleProfile(
        role=RoleType.FREELANCER,
        defaults={
            BeliefParameter.PEAK_ENERGY: 11.5,
            BeliefParameter.DEEP_WORK_TOLERANCE: 60.0,
            BeliefParameter.MEETING_TOLERANCE: 0.3,
            BeliefParameter.CONTEXT_SWITCH_COST: 0.5,
            BeliefParameter.CHAOS_TOLERANCE: 0.6,
            BeliefParameter.RECOVERY_RATE: 0.10,
            BeliefParameter.GUIDANCE_LEVEL: 0.3,
        },
        default_policies=[
            {"description": "Protect morning focus block", "condition": "time >= 09:00 AND time <= 12:00 AND activity = MEETING", "action": "warn"},
            {"description": "Break after 3 hours continuous work", "condition": "continuous_work_minutes >= 180", "action": "insert_break"},
        ],
    ),
    RoleType.MANAGER: RoleProfile(
        role=RoleType.MANAGER,
        defaults={
            BeliefParameter.PEAK_ENERGY: 9.5,
            BeliefParameter.DEEP_WORK_TOLERANCE: 30.0,
            BeliefParameter.MEETING_TOLERANCE: 0.8,
            BeliefParameter.CONTEXT_SWITCH_COST: 0.3,
            BeliefParameter.CHAOS_TOLERANCE: 0.7,
            BeliefParameter.RECOVERY_RATE: 0.15,
            BeliefParameter.GUIDANCE_LEVEL: 0.3,
        },
        default_policies=[
            {"description": "Mandatory break after 3 consecutive meetings", "condition": "consecutive_meetings >= 3", "action": "insert_break"},
            {"description": "Protect one deep work slot per day", "condition": "daily_deep_work_blocks == 0 AND time > 15:00", "action": "warn"},
        ],
    ),
    RoleType.CREATIVE: RoleProfile(
        role=RoleType.CREATIVE,
        defaults={
            BeliefParameter.PEAK_ENERGY: 23.5,
            BeliefParameter.DEEP_WORK_TOLERANCE: 120.0,
            BeliefParameter.MEETING_TOLERANCE: 0.2,
            BeliefParameter.CONTEXT_SWITCH_COST: 0.8,
            BeliefParameter.CHAOS_TOLERANCE: 0.3,
            BeliefParameter.RECOVERY_RATE: 0.07,
            BeliefParameter.GUIDANCE_LEVEL: 0.5,
        },
        default_policies=[
            {"description": "No meetings during peak creative hours", "condition": "time >= 22:00 AND activity = MEETING", "action": "block"},
            {"description": "Long buffer after context switch", "condition": "context_switch = true", "action": "insert_buffer_20min"},
        ],
    ),
}


def get_role_profile(role: RoleType) -> RoleProfile:
    return _ROLE_PROFILES[role]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/test_role_profile.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add backend/app/models/role_profile.py backend/tests/__init__.py backend/tests/test_role_profile.py
git commit -m "feat: add BeliefParameter enum and RoleProfile model with 5 role definitions"
```

---

## Task 2: UserBelief Model + Update Logic

**Files:**
- Create: `backend/app/models/user_belief.py`
- Test: `backend/tests/test_user_belief.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_user_belief.py
from datetime import datetime, timedelta
from app.models.user_belief import UserBelief
from app.models.role_profile import BeliefParameter


def test_create_belief():
    b = UserBelief(parameter=BeliefParameter.PEAK_ENERGY, belief_value=22.0, confidence=0.5)
    assert b.belief_value == 22.0
    assert b.confidence == 0.5
    assert b.evidence_count == 0


def test_update_simple():
    b = UserBelief(parameter=BeliefParameter.CHAOS_TOLERANCE, belief_value=0.4, confidence=0.5)
    b2 = b.update(observation=0.7, signal_weight=0.3)
    # new_belief = (0.4 * 0.5 + 0.7 * 0.3) / (0.5 + 0.3) = (0.2 + 0.21) / 0.8 = 0.5125
    assert abs(b2.belief_value - 0.5125) < 0.001
    # new_confidence = min(0.5 + 0.3 * 0.1, 0.95) = 0.53
    assert abs(b2.confidence - 0.53) < 0.001
    assert b2.evidence_count == 1


def test_update_peak_energy_wrapping():
    """11pm belief + 1am observation should move toward 1am, not 12pm."""
    b = UserBelief(parameter=BeliefParameter.PEAK_ENERGY, belief_value=23.0, confidence=0.5)
    b2 = b.update(observation=1.0, signal_weight=0.3)
    # Adjusted observation: 1.0 + 24 = 25.0
    # new_belief = (23.0 * 0.5 + 25.0 * 0.3) / 0.8 = (11.5 + 7.5) / 0.8 = 23.75
    # Normalize: 23.75 % 24 = 23.75
    assert abs(b2.belief_value - 23.75) < 0.01


def test_update_peak_energy_no_wrapping():
    """2pm belief + 4pm observation — no wrapping needed."""
    b = UserBelief(parameter=BeliefParameter.PEAK_ENERGY, belief_value=14.0, confidence=0.5)
    b2 = b.update(observation=16.0, signal_weight=0.3)
    # new_belief = (14.0 * 0.5 + 16.0 * 0.3) / 0.8 = (7.0 + 4.8) / 0.8 = 14.75
    assert abs(b2.belief_value - 14.75) < 0.01


def test_confidence_cap():
    b = UserBelief(parameter=BeliefParameter.CHAOS_TOLERANCE, belief_value=0.5, confidence=0.94)
    b2 = b.update(observation=0.5, signal_weight=0.5)
    assert b2.confidence <= 0.95


def test_confidence_decay():
    b = UserBelief(
        parameter=BeliefParameter.CHAOS_TOLERANCE,
        belief_value=0.5,
        confidence=0.8,
        last_updated=datetime.now() - timedelta(days=5),
    )
    b2 = b.with_decay()
    # 5 days * 0.01/day = 0.05 decay
    assert abs(b2.confidence - 0.75) < 0.001


def test_confidence_floor():
    b = UserBelief(
        parameter=BeliefParameter.CHAOS_TOLERANCE,
        belief_value=0.5,
        confidence=0.22,
        last_updated=datetime.now() - timedelta(days=10),
    )
    b2 = b.with_decay()
    # 0.22 - 0.10 = 0.12, but floor is 0.2
    assert b2.confidence == 0.2


def test_immutability():
    """update() returns a new object, doesn't mutate original."""
    b = UserBelief(parameter=BeliefParameter.CHAOS_TOLERANCE, belief_value=0.5, confidence=0.5)
    b2 = b.update(observation=0.8, signal_weight=0.3)
    assert b.belief_value == 0.5  # original unchanged
    assert b2.belief_value != 0.5  # new one changed
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/test_user_belief.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.user_belief'`

- [ ] **Step 3: Implement UserBelief**

```python
# backend/app/models/user_belief.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.models.role_profile import BeliefParameter

CONFIDENCE_CAP = 0.95
CONFIDENCE_FLOOR = 0.2
CONFIDENCE_DECAY_PER_DAY = 0.01


@dataclass(frozen=True)
class UserBelief:
    parameter: BeliefParameter
    belief_value: float
    confidence: float = 0.5
    last_updated: datetime = field(default_factory=datetime.now)
    evidence_count: int = 0

    def update(self, observation: float, signal_weight: float) -> UserBelief:
        adjusted_obs = self._adjust_observation(observation)
        new_value = (
            (self.belief_value * self.confidence + adjusted_obs * signal_weight)
            / (self.confidence + signal_weight)
        )
        if self.parameter == BeliefParameter.PEAK_ENERGY:
            new_value = new_value % 24.0
        new_confidence = min(self.confidence + signal_weight * 0.1, CONFIDENCE_CAP)
        return UserBelief(
            parameter=self.parameter,
            belief_value=new_value,
            confidence=new_confidence,
            last_updated=datetime.now(),
            evidence_count=self.evidence_count + 1,
        )

    def with_decay(self) -> UserBelief:
        days_since = (datetime.now() - self.last_updated).total_seconds() / 86400
        decay = days_since * CONFIDENCE_DECAY_PER_DAY
        new_confidence = max(self.confidence - decay, CONFIDENCE_FLOOR)
        return UserBelief(
            parameter=self.parameter,
            belief_value=self.belief_value,
            confidence=new_confidence,
            last_updated=self.last_updated,
            evidence_count=self.evidence_count,
        )

    def _adjust_observation(self, observation: float) -> float:
        if self.parameter != BeliefParameter.PEAK_ENERGY:
            return observation
        diff = abs(self.belief_value - observation)
        if diff > 12.0:
            if observation < self.belief_value:
                return observation + 24.0
            else:
                return observation - 24.0
        return observation
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/test_user_belief.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add backend/app/models/user_belief.py backend/tests/test_user_belief.py
git commit -m "feat: add UserBelief model with weighted-average update and confidence decay"
```

---

## Task 3: BeliefUpdater Service

**Files:**
- Create: `backend/app/services/belief_updater.py`
- Test: `backend/tests/test_belief_updater.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_belief_updater.py
from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief
from app.services.belief_updater import BeliefUpdater, SignalType


def _make_beliefs() -> dict[BeliefParameter, UserBelief]:
    return {
        BeliefParameter.PEAK_ENERGY: UserBelief(parameter=BeliefParameter.PEAK_ENERGY, belief_value=22.0),
        BeliefParameter.DEEP_WORK_TOLERANCE: UserBelief(parameter=BeliefParameter.DEEP_WORK_TOLERANCE, belief_value=45.0),
        BeliefParameter.CONTEXT_SWITCH_COST: UserBelief(parameter=BeliefParameter.CONTEXT_SWITCH_COST, belief_value=0.7),
        BeliefParameter.CHAOS_TOLERANCE: UserBelief(parameter=BeliefParameter.CHAOS_TOLERANCE, belief_value=0.4),
        BeliefParameter.MEETING_TOLERANCE: UserBelief(parameter=BeliefParameter.MEETING_TOLERANCE, belief_value=0.3),
        BeliefParameter.RECOVERY_RATE: UserBelief(parameter=BeliefParameter.RECOVERY_RATE, belief_value=0.15),
        BeliefParameter.GUIDANCE_LEVEL: UserBelief(parameter=BeliefParameter.GUIDANCE_LEVEL, belief_value=0.5),
    }


def test_signal_type_weights():
    assert SignalType.BLOCK_COMPLETION.weight == 0.3
    assert SignalType.RESCHEDULE.weight == 0.4
    assert SignalType.SELF_SCHEDULED.weight == 0.2
    assert SignalType.ENERGY_SELF_REPORT.weight == 0.5


def test_process_block_completed():
    updater = BeliefUpdater()
    beliefs = _make_beliefs()
    updated = updater.process_block_completion(
        beliefs=beliefs,
        block_start_hour=14.0,
        block_duration_minutes=45.0,
        status="completed",
    )
    # peak_energy should shift toward 14.0
    assert updated[BeliefParameter.PEAK_ENERGY].belief_value < 22.0
    # deep_work_tolerance should stay near 45.0 (completed full block)
    assert abs(updated[BeliefParameter.DEEP_WORK_TOLERANCE].belief_value - 45.0) < 5.0


def test_process_block_skipped():
    updater = BeliefUpdater()
    beliefs = _make_beliefs()
    updated = updater.process_block_completion(
        beliefs=beliefs,
        block_start_hour=22.0,
        block_duration_minutes=45.0,
        status="skipped",
    )
    # peak_energy should move AWAY from 22.0 (skip = opposite signal)
    # opposite_of(22.0) = 10.0 (since 22 > 12)
    assert updated[BeliefParameter.PEAK_ENERGY].belief_value < 22.0


def test_process_reschedule():
    updater = BeliefUpdater()
    beliefs = _make_beliefs()
    updated = updater.process_reschedule(
        beliefs=beliefs,
        original_hour=22.0,
        new_hour=15.0,
    )
    # Should shift peak toward new_hour (15.0)
    assert updated[BeliefParameter.PEAK_ENERGY].belief_value < 22.0


def test_process_energy_report():
    updater = BeliefUpdater()
    beliefs = _make_beliefs()
    updated = updater.process_energy_report(
        beliefs=beliefs,
        current_hour=14.0,
        level="great",
    )
    # "great" = 0.9, should shift peak toward 14.0
    assert updated[BeliefParameter.PEAK_ENERGY].belief_value < 22.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/test_belief_updater.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement BeliefUpdater**

```python
# backend/app/services/belief_updater.py
from __future__ import annotations

from enum import Enum

from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief


class SignalType(Enum):
    BLOCK_COMPLETION = ("block_completion", 0.3)
    RESCHEDULE = ("reschedule", 0.4)
    SELF_SCHEDULED = ("self_scheduled", 0.2)
    ENERGY_SELF_REPORT = ("energy_self_report", 0.5)

    def __init__(self, label: str, weight: float) -> None:
        self.label = label
        self.weight = weight


ENERGY_REPORT_MAP = {"low": 0.3, "ok": 0.6, "great": 0.9}


class BeliefUpdater:
    def process_block_completion(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        block_start_hour: float,
        block_duration_minutes: float,
        status: str,
    ) -> dict[BeliefParameter, UserBelief]:
        updated = dict(beliefs)
        w = SignalType.BLOCK_COMPLETION.weight

        if status == "completed":
            peak_obs = block_start_hour
            duration_obs = block_duration_minutes
        elif status == "skipped":
            peak_obs = 10.0 if block_start_hour >= 12.0 else 20.0
            duration_obs = None
        elif status == "partial":
            peak_obs = block_start_hour
            duration_obs = block_duration_minutes * 0.5
        else:
            return updated

        updated[BeliefParameter.PEAK_ENERGY] = beliefs[BeliefParameter.PEAK_ENERGY].update(peak_obs, w)
        if duration_obs is not None:
            updated[BeliefParameter.DEEP_WORK_TOLERANCE] = beliefs[BeliefParameter.DEEP_WORK_TOLERANCE].update(duration_obs, w)

        return updated

    def process_reschedule(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        original_hour: float,
        new_hour: float,
    ) -> dict[BeliefParameter, UserBelief]:
        updated = dict(beliefs)
        w = SignalType.RESCHEDULE.weight
        updated[BeliefParameter.PEAK_ENERGY] = beliefs[BeliefParameter.PEAK_ENERGY].update(new_hour, w)
        return updated

    def process_self_scheduled(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        chosen_hour: float,
        block_duration_minutes: float,
    ) -> dict[BeliefParameter, UserBelief]:
        updated = dict(beliefs)
        w = SignalType.SELF_SCHEDULED.weight
        updated[BeliefParameter.PEAK_ENERGY] = beliefs[BeliefParameter.PEAK_ENERGY].update(chosen_hour, w)
        updated[BeliefParameter.DEEP_WORK_TOLERANCE] = beliefs[BeliefParameter.DEEP_WORK_TOLERANCE].update(block_duration_minutes, w)
        return updated

    def process_energy_report(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        current_hour: float,
        level: str,
    ) -> dict[BeliefParameter, UserBelief]:
        updated = dict(beliefs)
        w = SignalType.ENERGY_SELF_REPORT.weight
        energy_value = ENERGY_REPORT_MAP.get(level, 0.6)
        if energy_value >= 0.7:
            updated[BeliefParameter.PEAK_ENERGY] = beliefs[BeliefParameter.PEAK_ENERGY].update(current_hour, w)
        return updated
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/test_belief_updater.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add backend/app/services/belief_updater.py backend/tests/test_belief_updater.py
git commit -m "feat: add BeliefUpdater service with signal processing for all 4 signal types"
```

---

## Task 4: SchedulingContext Model + Resolution Function

**Files:**
- Create: `backend/app/models/scheduling_context.py`
- Test: `backend/tests/test_scheduling_context.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_scheduling_context.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/test_scheduling_context.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement SchedulingContext**

```python
# backend/app/models/scheduling_context.py
from __future__ import annotations

from dataclasses import dataclass

from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief


@dataclass(frozen=True)
class SchedulingContext:
    peak_energy_start: float
    peak_energy_end: float
    max_block_duration_minutes: float
    min_buffer_minutes: float
    initial_chaos_tolerance: float
    max_consecutive_meetings: int
    cognitive_recovery_rate: float
    guidance_level: float = 0.5


def resolve_beliefs(beliefs: dict[BeliefParameter, UserBelief]) -> SchedulingContext:
    peak = beliefs[BeliefParameter.PEAK_ENERGY].belief_value
    return SchedulingContext(
        peak_energy_start=peak - 1.5,
        peak_energy_end=peak + 1.5,
        max_block_duration_minutes=beliefs[BeliefParameter.DEEP_WORK_TOLERANCE].belief_value,
        min_buffer_minutes=beliefs[BeliefParameter.CONTEXT_SWITCH_COST].belief_value * 30,
        initial_chaos_tolerance=beliefs[BeliefParameter.CHAOS_TOLERANCE].belief_value,
        max_consecutive_meetings=round(beliefs[BeliefParameter.MEETING_TOLERANCE].belief_value * 5),
        cognitive_recovery_rate=beliefs[BeliefParameter.RECOVERY_RATE].belief_value,
        guidance_level=beliefs[BeliefParameter.GUIDANCE_LEVEL].belief_value,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/test_scheduling_context.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add backend/app/models/scheduling_context.py backend/tests/test_scheduling_context.py
git commit -m "feat: add SchedulingContext model and belief resolution function"
```

---

## Task 5: Adaptive Questionnaire Service

**Files:**
- Create: `backend/app/services/adaptive_questionnaire.py`
- Test: `backend/tests/test_adaptive_questionnaire.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_adaptive_questionnaire.py
from app.models.role_profile import BeliefParameter, RoleType
from app.services.adaptive_questionnaire import AdaptiveQuestionnaire


def test_init_with_role():
    aq = AdaptiveQuestionnaire(RoleType.STUDENT)
    assert aq.role.value == "student"
    assert len(aq.pending_questions) == 3  # 3 core questions


def test_get_first_question():
    aq = AdaptiveQuestionnaire(RoleType.STUDENT)
    q = aq.get_next_question()
    assert q is not None
    assert q["id"] == "energy_peak"
    assert len(q["options"]) == 4


def test_answer_no_conflict():
    """Student defaults to Late Night (22.0). Answering Late Night = no follow-up triggered."""
    aq = AdaptiveQuestionnaire(RoleType.STUDENT)
    aq.get_next_question()
    result = aq.submit_answer("energy_peak", "Late Night")
    assert result["conflict"] is False


def test_answer_with_conflict():
    """Student defaults to Late Night (22.0). Answering Morning (9.0) = conflict."""
    aq = AdaptiveQuestionnaire(RoleType.STUDENT)
    aq.get_next_question()
    result = aq.submit_answer("energy_peak", "Morning")
    assert result["conflict"] is True
    # Should have added a follow-up question
    assert len(aq.pending_questions) > 2  # was 2 remaining, now has follow-up


def test_full_flow_min_questions():
    """Answering all questions with role-matching answers = 3 core only."""
    aq = AdaptiveQuestionnaire(RoleType.STUDENT)
    # Q1: energy_peak — Late Night matches Student
    aq.get_next_question()
    aq.submit_answer("energy_peak", "Late Night")
    # Q2: focus_duration — Under 30 min closest to 45 min
    aq.get_next_question()
    aq.submit_answer("focus_duration", "30-60 min")
    # Q3: drain_source
    aq.get_next_question()
    aq.submit_answer("drain_source", "Context switching")
    # No more questions
    assert aq.get_next_question() is None


def test_get_beliefs():
    aq = AdaptiveQuestionnaire(RoleType.STUDENT)
    aq.get_next_question()
    aq.submit_answer("energy_peak", "Morning")
    aq.get_next_question()
    aq.submit_answer("focus_duration", "30-60 min")
    aq.get_next_question()
    aq.submit_answer("drain_source", "Meetings")

    beliefs = aq.get_beliefs()
    assert BeliefParameter.PEAK_ENERGY in beliefs
    # Should be Morning (9.0), not Student default (22.0)
    assert beliefs[BeliefParameter.PEAK_ENERGY].belief_value == 9.0
    # Meetings drain → meeting_tolerance should decrease from 0.3
    assert beliefs[BeliefParameter.MEETING_TOLERANCE].belief_value < 0.3


def test_get_summary():
    aq = AdaptiveQuestionnaire(RoleType.STUDENT)
    aq.get_next_question()
    aq.submit_answer("energy_peak", "Late Night")
    aq.get_next_question()
    aq.submit_answer("focus_duration", "30-60 min")
    aq.get_next_question()
    aq.submit_answer("drain_source", "Context switching")

    summary = aq.get_summary()
    assert isinstance(summary, str)
    assert len(summary) > 20
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/test_adaptive_questionnaire.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement AdaptiveQuestionnaire**

```python
# backend/app/services/adaptive_questionnaire.py
from __future__ import annotations

from app.models.role_profile import BeliefParameter, RoleType, get_role_profile, RoleProfile
from app.models.user_belief import UserBelief

ENERGY_ENCODING = {"Morning": 9.0, "Afternoon": 14.0, "Evening": 20.0, "Late Night": 23.0}
FOCUS_ENCODING = {"Under 30 min": 25.0, "30-60 min": 45.0, "1-2 hours": 90.0, "2+ hours": 150.0}

CORE_QUESTIONS = [
    {
        "id": "energy_peak",
        "text": "When do you feel sharpest?",
        "options": ["Morning", "Afternoon", "Evening", "Late Night"],
        "parameter": BeliefParameter.PEAK_ENERGY,
        "encoding": ENERGY_ENCODING,
        "range": 24.0,
    },
    {
        "id": "focus_duration",
        "text": "How long can you focus without a break?",
        "options": ["Under 30 min", "30-60 min", "1-2 hours", "2+ hours"],
        "parameter": BeliefParameter.DEEP_WORK_TOLERANCE,
        "encoding": FOCUS_ENCODING,
        "range": 165.0,  # 180 - 15
    },
    {
        "id": "drain_source",
        "text": "What drains you most?",
        "options": ["Meetings", "Context switching", "Unclear tasks", "Long focus sessions"],
        "parameter": None,  # affects multiple parameters
        "encoding": None,
        "range": None,
    },
]

FOLLOW_UPS = {
    "energy_conflict": {
        "id": "schedule_flexibility",
        "text": "Do you have a fixed schedule (classes/office) or flexible hours?",
        "options": ["Fixed schedule", "Mostly fixed", "Flexible", "Fully flexible"],
    },
    "focus_conflict": {
        "id": "work_pattern",
        "text": "Do you work in one long stretch or multiple short ones?",
        "options": ["One long stretch", "A few medium stretches", "Many short bursts"],
    },
    "chaos_unclear": {
        "id": "disruption_response",
        "text": "When your plan gets disrupted, do you rework it or push through?",
        "options": ["Rework completely", "Adjust and continue", "Push through"],
    },
    "meeting_unclear": {
        "id": "meeting_limit",
        "text": "How many meetings is too many in one day?",
        "options": ["2 is too many", "3-4 is fine", "5+ is fine", "No limit"],
    },
}

CONFLICT_THRESHOLD = 0.3


class AdaptiveQuestionnaire:
    def __init__(self, role: RoleType) -> None:
        self.role = role
        self.profile: RoleProfile = get_role_profile(role)
        self.pending_questions: list[dict] = list(CORE_QUESTIONS)
        self.answers: dict[str, str] = {}
        self._belief_adjustments: dict[BeliefParameter, float] = {}

    def get_next_question(self) -> dict | None:
        if not self.pending_questions:
            return None
        q = self.pending_questions[0]
        return {"id": q["id"], "text": q["text"], "options": q["options"]}

    def submit_answer(self, question_id: str, answer: str) -> dict:
        q = self.pending_questions.pop(0)
        assert q["id"] == question_id
        self.answers[question_id] = answer

        conflict = False

        if question_id == "energy_peak":
            encoded = ENERGY_ENCODING[answer]
            self._belief_adjustments[BeliefParameter.PEAK_ENERGY] = encoded
            default = self.profile.defaults[BeliefParameter.PEAK_ENERGY]
            # Circular distance for peak_energy
            diff = abs(encoded - default)
            dist = min(diff, 24.0 - diff)
            conflict_score = dist / 24.0
            if conflict_score > CONFLICT_THRESHOLD:
                conflict = True
                self.pending_questions.insert(0, FOLLOW_UPS["energy_conflict"])

        elif question_id == "focus_duration":
            encoded = FOCUS_ENCODING[answer]
            self._belief_adjustments[BeliefParameter.DEEP_WORK_TOLERANCE] = encoded
            default = self.profile.defaults[BeliefParameter.DEEP_WORK_TOLERANCE]
            conflict_score = abs(encoded - default) / 165.0
            if conflict_score > CONFLICT_THRESHOLD:
                conflict = True
                self.pending_questions.insert(0, FOLLOW_UPS["focus_conflict"])

        elif question_id == "drain_source":
            if answer == "Meetings":
                default = self.profile.defaults[BeliefParameter.MEETING_TOLERANCE]
                self._belief_adjustments[BeliefParameter.MEETING_TOLERANCE] = max(default - 0.2, 0.0)
            elif answer == "Context switching":
                default = self.profile.defaults[BeliefParameter.CONTEXT_SWITCH_COST]
                self._belief_adjustments[BeliefParameter.CONTEXT_SWITCH_COST] = min(default + 0.2, 1.0)
            elif answer == "Long focus sessions":
                default = self.profile.defaults[BeliefParameter.DEEP_WORK_TOLERANCE]
                self._belief_adjustments[BeliefParameter.DEEP_WORK_TOLERANCE] = max(default - 15.0, 15.0)

        # Follow-up answers adjust chaos/meeting tolerance
        elif question_id == "disruption_response":
            mapping = {"Rework completely": 0.3, "Adjust and continue": 0.5, "Push through": 0.7}
            self._belief_adjustments[BeliefParameter.CHAOS_TOLERANCE] = mapping.get(answer, 0.5)

        elif question_id == "meeting_limit":
            mapping = {"2 is too many": 0.2, "3-4 is fine": 0.5, "5+ is fine": 0.8, "No limit": 0.9}
            self._belief_adjustments[BeliefParameter.MEETING_TOLERANCE] = mapping.get(answer, 0.5)

        return {"conflict": conflict}

    def get_beliefs(self) -> dict[BeliefParameter, UserBelief]:
        beliefs = {}
        for param in BeliefParameter:
            if param in self._belief_adjustments:
                value = self._belief_adjustments[param]
            else:
                value = self.profile.defaults[param]
            beliefs[param] = UserBelief(parameter=param, belief_value=value, confidence=0.5)
        return beliefs

    def get_summary(self) -> str:
        beliefs = self.get_beliefs()
        peak = beliefs[BeliefParameter.PEAK_ENERGY].belief_value
        duration = beliefs[BeliefParameter.DEEP_WORK_TOLERANCE].belief_value
        switch_cost = beliefs[BeliefParameter.CONTEXT_SWITCH_COST].belief_value

        if peak >= 21 or peak < 4:
            time_desc = "late-night"
        elif peak >= 17:
            time_desc = "evening"
        elif peak >= 12:
            time_desc = "afternoon"
        else:
            time_desc = "morning"

        if duration <= 30:
            dur_desc = "short"
        elif duration <= 60:
            dur_desc = f"{int(duration)}-minute"
        else:
            dur_desc = f"{int(duration)}-minute"

        buffer_desc = "long" if switch_cost > 0.5 else "short"

        return (
            f"You're set up for {time_desc} deep work in {dur_desc} sprints, "
            f"with {buffer_desc} breaks between context switches. "
            f"We'll learn more as you use the app."
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/test_adaptive_questionnaire.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add backend/app/services/adaptive_questionnaire.py backend/tests/test_adaptive_questionnaire.py
git commit -m "feat: add adaptive questionnaire with conflict detection and follow-up questions"
```

---

## Task 6: CheckInGenerator Service

**Files:**
- Create: `backend/app/services/checkin_generator.py`
- Test: `backend/tests/test_checkin_generator.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_checkin_generator.py
from datetime import datetime, timedelta
from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief
from app.services.checkin_generator import CheckInGenerator


def _make_beliefs(confidences: dict[BeliefParameter, float] | None = None) -> dict[BeliefParameter, UserBelief]:
    default_conf = 0.5
    c = confidences or {}
    return {
        param: UserBelief(
            parameter=param,
            belief_value=0.5,
            confidence=c.get(param, default_conf),
        )
        for param in BeliefParameter
    }


def test_picks_lowest_confidence():
    beliefs = _make_beliefs({
        BeliefParameter.PEAK_ENERGY: 0.8,
        BeliefParameter.DEEP_WORK_TOLERANCE: 0.3,  # lowest
        BeliefParameter.CONTEXT_SWITCH_COST: 0.6,
        BeliefParameter.CHAOS_TOLERANCE: 0.7,
        BeliefParameter.MEETING_TOLERANCE: 0.5,
        BeliefParameter.RECOVERY_RATE: 0.6,
        BeliefParameter.GUIDANCE_LEVEL: 0.7,
    })
    gen = CheckInGenerator()
    result = gen.generate(beliefs, week_data={})
    assert result["parameter"] == BeliefParameter.DEEP_WORK_TOLERANCE.value


def test_skip_when_all_confident():
    beliefs = _make_beliefs({param: 0.85 for param in BeliefParameter})
    gen = CheckInGenerator()
    result = gen.generate(beliefs, week_data={})
    assert result["skip"] is True
    assert "good read" in result["message"].lower()


def test_generates_question_text():
    beliefs = _make_beliefs({BeliefParameter.CHAOS_TOLERANCE: 0.25})
    gen = CheckInGenerator()
    result = gen.generate(beliefs, week_data={})
    assert "question" in result
    assert isinstance(result["question"], str)
    assert len(result["options"]) >= 2


def test_returns_options():
    beliefs = _make_beliefs({BeliefParameter.PEAK_ENERGY: 0.2})
    gen = CheckInGenerator()
    result = gen.generate(beliefs, week_data={})
    assert "options" in result
    assert len(result["options"]) >= 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/test_checkin_generator.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement CheckInGenerator**

```python
# backend/app/services/checkin_generator.py
from __future__ import annotations

from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief

CONFIDENCE_SKIP_THRESHOLD = 0.8

QUESTION_TEMPLATES: dict[BeliefParameter, dict] = {
    BeliefParameter.PEAK_ENERGY: {
        "question": "When did you feel most productive this week?",
        "options": ["Morning", "Afternoon", "Evening", "Late Night"],
        "encoding": {"Morning": 9.0, "Afternoon": 14.0, "Evening": 20.0, "Late Night": 23.0},
    },
    BeliefParameter.DEEP_WORK_TOLERANCE: {
        "question": "How did your focus block lengths feel this week?",
        "options": ["Too short", "About right", "Too long"],
        "encoding": {"Too short": 1.3, "About right": 1.0, "Too long": 0.7},  # multipliers
    },
    BeliefParameter.CONTEXT_SWITCH_COST: {
        "question": "How did back-to-back task switches feel this week?",
        "options": ["Exhausting", "Manageable", "No problem"],
        "encoding": {"Exhausting": 0.9, "Manageable": 0.5, "No problem": 0.2},
    },
    BeliefParameter.CHAOS_TOLERANCE: {
        "question": "When your schedule got disrupted this week, how did it feel?",
        "options": ["Threw me off", "Mildly annoying", "Didn't bother me"],
        "encoding": {"Threw me off": 0.2, "Mildly annoying": 0.5, "Didn't bother me": 0.8},
    },
    BeliefParameter.MEETING_TOLERANCE: {
        "question": "How did your meeting load feel this week?",
        "options": ["Too many", "About right", "Could handle more"],
        "encoding": {"Too many": 0.2, "About right": 0.5, "Could handle more": 0.8},
    },
    BeliefParameter.RECOVERY_RATE: {
        "question": "After intense focus blocks, did your breaks feel long enough?",
        "options": ["Needed more time", "Just right", "Could've been shorter"],
        "encoding": {"Needed more time": 0.05, "Just right": 0.10, "Could've been shorter": 0.18},
    },
    BeliefParameter.GUIDANCE_LEVEL: {
        "question": "How did the amount of prompts and suggestions feel this week?",
        "options": ["Too many", "Just right", "Want more"],
        "encoding": {"Too many": 0.2, "Just right": 0.5, "Want more": 0.8},
    },
}


class CheckInGenerator:
    def generate(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        week_data: dict,
    ) -> dict:
        # Check if all confidence scores are above threshold
        if all(b.confidence > CONFIDENCE_SKIP_THRESHOLD for b in beliefs.values()):
            return {
                "skip": True,
                "message": "Looks like we've got a good read on you this week.",
            }

        # Find parameter with lowest confidence
        lowest_param = min(beliefs, key=lambda p: beliefs[p].confidence)
        template = QUESTION_TEMPLATES[lowest_param]

        return {
            "skip": False,
            "parameter": lowest_param.value,
            "question": template["question"],
            "options": template["options"],
            "encoding": template["encoding"],
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/test_checkin_generator.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add backend/app/services/checkin_generator.py backend/tests/test_checkin_generator.py
git commit -m "feat: add CheckInGenerator service for weekly lowest-confidence check-ins"
```

---

## Task 7: Database Changes (UserBeliefORM + ScheduledBlockORM status + UserORM role)

**Files:**
- Modify: `backend/app/db/models.py:17-93`

- [ ] **Step 1: Add BlockStatus enum, role field, status field, and UserBeliefORM**

Add to `backend/app/db/models.py` — import `Enum` from sqlalchemy, add after existing imports:

```python
# Add to imports at top:
import enum

# Add enum class before UserORM:
class BlockStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    PARTIAL = "partial"
    RESCHEDULED = "rescheduled"
```

Modify `UserORM` (lines 17-23) — add `role` column:
```python
role = Column(String, nullable=True)  # RoleType value
```

Modify `ScheduledBlockORM` (lines 78-93) — add `status` column:
```python
status = Column(String, default="scheduled", nullable=False)
```

Add new `UserBeliefORM` class after `TimelineChangeORM`:
```python
class UserBeliefORM(Base):
    __tablename__ = "user_beliefs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    parameter = Column(String, nullable=False)  # BeliefParameter value
    belief_value = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False, default=0.5)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    evidence_count = Column(Integer, default=0, nullable=False)
```

- [ ] **Step 2: Verify the model file loads without errors**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -c "from app.db.models import UserBeliefORM, BlockStatus; print('OK')" `
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add backend/app/db/models.py
git commit -m "feat: add UserBeliefORM table, BlockStatus enum, role/status columns"
```

---

## Task 8: BehavioralTracker Service

**Files:**
- Create: `backend/app/services/behavioral_tracker.py`
- Test: `backend/tests/test_behavioral_tracker.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_behavioral_tracker.py
from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief
from app.services.behavioral_tracker import BehavioralTracker


def _make_beliefs() -> dict[BeliefParameter, UserBelief]:
    return {
        BeliefParameter.PEAK_ENERGY: UserBelief(parameter=BeliefParameter.PEAK_ENERGY, belief_value=22.0),
        BeliefParameter.DEEP_WORK_TOLERANCE: UserBelief(parameter=BeliefParameter.DEEP_WORK_TOLERANCE, belief_value=45.0),
        BeliefParameter.CONTEXT_SWITCH_COST: UserBelief(parameter=BeliefParameter.CONTEXT_SWITCH_COST, belief_value=0.7),
        BeliefParameter.CHAOS_TOLERANCE: UserBelief(parameter=BeliefParameter.CHAOS_TOLERANCE, belief_value=0.4),
        BeliefParameter.MEETING_TOLERANCE: UserBelief(parameter=BeliefParameter.MEETING_TOLERANCE, belief_value=0.3),
        BeliefParameter.RECOVERY_RATE: UserBelief(parameter=BeliefParameter.RECOVERY_RATE, belief_value=0.15),
        BeliefParameter.GUIDANCE_LEVEL: UserBelief(parameter=BeliefParameter.GUIDANCE_LEVEL, belief_value=0.5),
    }


def test_track_block_completion():
    tracker = BehavioralTracker()
    beliefs = _make_beliefs()
    updated = tracker.on_block_status_change(
        beliefs=beliefs,
        block_start_hour=14.0,
        block_duration_minutes=45.0,
        new_status="completed",
    )
    assert updated[BeliefParameter.PEAK_ENERGY].belief_value != 22.0


def test_track_reschedule():
    tracker = BehavioralTracker()
    beliefs = _make_beliefs()
    updated = tracker.on_reschedule(
        beliefs=beliefs,
        original_hour=22.0,
        new_hour=15.0,
    )
    assert updated[BeliefParameter.PEAK_ENERGY].belief_value < 22.0


def test_track_self_schedule():
    tracker = BehavioralTracker()
    beliefs = _make_beliefs()
    updated = tracker.on_self_scheduled(
        beliefs=beliefs,
        chosen_hour=10.0,
        duration_minutes=60.0,
    )
    assert updated[BeliefParameter.PEAK_ENERGY].belief_value < 22.0
    assert updated[BeliefParameter.DEEP_WORK_TOLERANCE].belief_value != 45.0


def test_track_energy_report():
    tracker = BehavioralTracker()
    beliefs = _make_beliefs()
    updated = tracker.on_energy_report(
        beliefs=beliefs,
        current_hour=10.0,
        level="great",
    )
    assert updated[BeliefParameter.PEAK_ENERGY].belief_value < 22.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/test_behavioral_tracker.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement BehavioralTracker**

```python
# backend/app/services/behavioral_tracker.py
from __future__ import annotations

from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief
from app.services.belief_updater import BeliefUpdater


class BehavioralTracker:
    def __init__(self) -> None:
        self._updater = BeliefUpdater()

    def on_block_status_change(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        block_start_hour: float,
        block_duration_minutes: float,
        new_status: str,
    ) -> dict[BeliefParameter, UserBelief]:
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
        return self._updater.process_reschedule(
            beliefs=beliefs,
            original_hour=original_hour,
            new_hour=new_hour,
        )

    def on_self_scheduled(
        self,
        beliefs: dict[BeliefParameter, UserBelief],
        chosen_hour: float,
        duration_minutes: float,
    ) -> dict[BeliefParameter, UserBelief]:
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
        return self._updater.process_energy_report(
            beliefs=beliefs,
            current_hour=current_hour,
            level=level,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/test_behavioral_tracker.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add backend/app/services/behavioral_tracker.py backend/tests/test_behavioral_tracker.py
git commit -m "feat: add BehavioralTracker service wrapping BeliefUpdater for signal routing"
```

---

## Task 9: API Endpoints — Onboarding (Role + Questionnaire)

**Files:**
- Modify: `backend/app/api/onboarding.py:1-292`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add role selection and adaptive questionnaire endpoints to onboarding.py**

Add two new endpoints to `backend/app/api/onboarding.py`:

```python
# POST /api/onboarding/role
@router.post("/role")
async def select_role(request: Request):
    body = await request.json()
    role_str = body.get("role", "").lower()
    try:
        role = RoleType(role_str)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": f"Invalid role: {role_str}"})

    aq = AdaptiveQuestionnaire(role)
    session_id = str(uuid.uuid4())
    _questionnaire_sessions[session_id] = aq

    first_question = aq.get_next_question()
    return {"session_id": session_id, "next_question": first_question}


# POST /api/onboarding/questionnaire
@router.post("/questionnaire")
async def submit_questionnaire_answer(request: Request):
    body = await request.json()
    session_id = body.get("session_id")
    question_id = body.get("question_id")
    answer = body.get("answer")

    aq = _questionnaire_sessions.get(session_id)
    if not aq:
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    result = aq.submit_answer(question_id, answer)
    next_q = aq.get_next_question()

    if next_q is None:
        summary = aq.get_summary()
        beliefs = aq.get_beliefs()
        return {"next_question": None, "summary": summary, "beliefs_initialized": True}

    return {"next_question": next_q, "summary": None, "conflict": result["conflict"]}
```

Add imports and session storage at top of file:
```python
import uuid
from app.models.role_profile import RoleType
from app.services.adaptive_questionnaire import AdaptiveQuestionnaire

_questionnaire_sessions: dict[str, AdaptiveQuestionnaire] = {}
```

- [ ] **Step 2: Test the endpoints manually**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -c "from app.api.onboarding import router; print('Endpoints loaded OK')"`
Expected: `Endpoints loaded OK`

- [ ] **Step 3: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add backend/app/api/onboarding.py
git commit -m "feat: add role selection and adaptive questionnaire API endpoints"
```

---

## Task 10: API Endpoints — Blocks, Self-Report, Check-in, Beliefs

**Files:**
- Create: `backend/app/api/blocks.py`
- Create: `backend/app/api/self_report.py`
- Create: `backend/app/api/checkin.py`
- Create: `backend/app/api/beliefs.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create blocks endpoint**

```python
# backend/app/api/blocks.py
from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/blocks", tags=["blocks"])


@router.patch("/{block_id}/status")
async def update_block_status(block_id: str, request: Request):
    body = await request.json()
    new_status = body.get("status")
    valid = {"completed", "skipped", "partial", "rescheduled", "in_progress"}
    if new_status not in valid:
        return JSONResponse(status_code=400, content={"error": f"Invalid status: {new_status}"})

    # TODO: persist to DB, trigger BehavioralTracker
    return {"updated": True, "block_id": block_id, "status": new_status}
```

- [ ] **Step 2: Create self-report endpoint**

```python
# backend/app/api/self_report.py
from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/self-report", tags=["self-report"])


@router.post("/energy")
async def submit_energy_report(request: Request):
    body = await request.json()
    level = body.get("level")
    block_id = body.get("block_id")

    if level not in ("low", "ok", "great"):
        return JSONResponse(status_code=400, content={"error": f"Invalid level: {level}"})

    # TODO: trigger BehavioralTracker with energy report
    return {"recorded": True, "level": level, "block_id": block_id}
```

- [ ] **Step 3: Create check-in endpoint**

```python
# backend/app/api/checkin.py
from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief
from app.services.checkin_generator import CheckInGenerator

router = APIRouter(prefix="/api/checkin", tags=["checkin"])

_checkin_generator = CheckInGenerator()

# In-memory beliefs store for MVP — replace with DB
_user_beliefs: dict[str, dict[BeliefParameter, UserBelief]] = {}


@router.get("/next")
async def get_next_checkin():
    user_id = "00000000-0000-0000-0000-000000000001"  # hardcoded for MVP
    beliefs = _user_beliefs.get(user_id)
    if not beliefs:
        return {"skip": True, "message": "No profile set up yet."}

    result = _checkin_generator.generate(beliefs, week_data={})
    return result


@router.post("/answer")
async def submit_checkin_answer(request: Request):
    body = await request.json()
    parameter = body.get("parameter")
    answer = body.get("answer")

    # TODO: decode answer using template encoding, update belief via BeliefUpdater
    return {"updated": True, "parameter": parameter}
```

- [ ] **Step 4: Create beliefs endpoint**

```python
# backend/app/api/beliefs.py
from fastapi import APIRouter

from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief

router = APIRouter(prefix="/api/beliefs", tags=["beliefs"])

# In-memory beliefs store for MVP — replace with DB
_user_beliefs: dict[str, dict[BeliefParameter, UserBelief]] = {}


@router.get("")
async def get_beliefs():
    user_id = "00000000-0000-0000-0000-000000000001"  # hardcoded for MVP
    beliefs = _user_beliefs.get(user_id, {})
    return {
        "beliefs": [
            {
                "parameter": param.value,
                "value": belief.belief_value,
                "confidence": belief.confidence,
            }
            for param, belief in beliefs.items()
        ]
    }
```

- [ ] **Step 5: Register all new routers in main.py**

Add to `backend/app/main.py`:
```python
from app.api.blocks import router as blocks_router
from app.api.self_report import router as self_report_router
from app.api.checkin import router as checkin_router
from app.api.beliefs import router as beliefs_router

app.include_router(blocks_router)
app.include_router(self_report_router)
app.include_router(checkin_router)
app.include_router(beliefs_router)
```

- [ ] **Step 6: Verify the app starts**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -c "from app.main import app; print(f'{len(app.routes)} routes loaded')"`
Expected: Route count increases, no import errors

- [ ] **Step 7: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add backend/app/api/blocks.py backend/app/api/self_report.py backend/app/api/checkin.py backend/app/api/beliefs.py backend/app/main.py
git commit -m "feat: add API endpoints for blocks, self-report, check-in, and beliefs"
```

---

## Task 11: Frontend — Role Selector Component

**Files:**
- Create: `frontend/src/components/RoleSelector.tsx`
- Create: `frontend/src/components/RoleSelector.module.css`

- [ ] **Step 1: Create RoleSelector component**

```tsx
// frontend/src/components/RoleSelector.tsx
import styles from './RoleSelector.module.css';

const ROLES = [
  { id: 'student', label: 'Student', icon: '📚', desc: 'Classes, study sessions, flexible schedule' },
  { id: 'professional', label: 'Professional', icon: '💼', desc: 'Office hours, meetings, structured day' },
  { id: 'freelancer', label: 'Freelancer', icon: '🎯', desc: 'Client work, self-managed, flexible' },
  { id: 'manager', label: 'Manager', icon: '👥', desc: 'Meetings, coordination, people-focused' },
  { id: 'creative', label: 'Creative', icon: '🎨', desc: 'Deep focus, irregular hours, flow-driven' },
];

interface Props {
  onSelect: (role: string) => void;
  selected: string | null;
}

export default function RoleSelector({ onSelect, selected }: Props) {
  return (
    <div className={styles.container}>
      <h2 className={styles.title}>What best describes you?</h2>
      <p className={styles.subtitle}>This helps us set up your schedule. You can always change it later.</p>
      <div className={styles.grid}>
        {ROLES.map((role) => (
          <button
            key={role.id}
            className={`${styles.card} ${selected === role.id ? styles.selected : ''}`}
            onClick={() => onSelect(role.id)}
          >
            <span className={styles.icon}>{role.icon}</span>
            <span className={styles.label}>{role.label}</span>
            <span className={styles.desc}>{role.desc}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create CSS module**

```css
/* frontend/src/components/RoleSelector.module.css */
.container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  padding: 2rem;
}
.title { font-size: 1.5rem; font-weight: 600; color: #e0e0e0; }
.subtitle { font-size: 0.9rem; color: #888; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; width: 100%; max-width: 600px; }
.card {
  display: flex; flex-direction: column; align-items: center; gap: 0.5rem;
  padding: 1.25rem; border-radius: 12px; border: 2px solid #333;
  background: #1a1a1a; cursor: pointer; transition: all 0.2s;
}
.card:hover { border-color: #555; background: #222; }
.selected { border-color: #4a9eff; background: #1a2a3a; }
.icon { font-size: 2rem; }
.label { font-size: 1rem; font-weight: 500; color: #e0e0e0; }
.desc { font-size: 0.75rem; color: #777; text-align: center; }
```

- [ ] **Step 3: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add frontend/src/components/RoleSelector.tsx frontend/src/components/RoleSelector.module.css
git commit -m "feat: add RoleSelector component with 5 role cards"
```

---

## Task 12: Frontend — AdaptiveQuestion + ProfileSummary Components

**Files:**
- Create: `frontend/src/components/AdaptiveQuestion.tsx`
- Create: `frontend/src/components/AdaptiveQuestion.module.css`
- Create: `frontend/src/components/ProfileSummary.tsx`
- Create: `frontend/src/components/ProfileSummary.module.css`

- [ ] **Step 1: Create AdaptiveQuestion component**

```tsx
// frontend/src/components/AdaptiveQuestion.tsx
import styles from './AdaptiveQuestion.module.css';

interface Question {
  id: string;
  text: string;
  options: string[];
}

interface Props {
  question: Question;
  onAnswer: (questionId: string, answer: string) => void;
}

export default function AdaptiveQuestion({ question, onAnswer }: Props) {
  return (
    <div className={styles.container}>
      <h2 className={styles.question}>{question.text}</h2>
      <div className={styles.options}>
        {question.options.map((opt) => (
          <button
            key={opt}
            className={styles.option}
            onClick={() => onAnswer(question.id, opt)}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create AdaptiveQuestion CSS**

```css
/* frontend/src/components/AdaptiveQuestion.module.css */
.container { display: flex; flex-direction: column; align-items: center; gap: 2rem; padding: 2rem; }
.question { font-size: 1.3rem; font-weight: 500; color: #e0e0e0; text-align: center; }
.options { display: flex; flex-direction: column; gap: 0.75rem; width: 100%; max-width: 400px; }
.option {
  padding: 1rem; border-radius: 10px; border: 2px solid #333;
  background: #1a1a1a; color: #e0e0e0; cursor: pointer;
  font-size: 1rem; text-align: center; transition: all 0.2s;
}
.option:hover { border-color: #4a9eff; background: #1a2a3a; }
```

- [ ] **Step 3: Create ProfileSummary component**

```tsx
// frontend/src/components/ProfileSummary.tsx
import styles from './ProfileSummary.module.css';

interface Props {
  summary: string;
  onContinue: () => void;
}

export default function ProfileSummary({ summary, onContinue }: Props) {
  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Your Profile</h2>
      <p className={styles.summary}>{summary}</p>
      <button className={styles.button} onClick={onContinue}>Continue</button>
    </div>
  );
}
```

- [ ] **Step 4: Create ProfileSummary CSS**

```css
/* frontend/src/components/ProfileSummary.module.css */
.container { display: flex; flex-direction: column; align-items: center; gap: 1.5rem; padding: 2rem; }
.title { font-size: 1.3rem; font-weight: 600; color: #e0e0e0; }
.summary { font-size: 1rem; color: #aaa; text-align: center; max-width: 500px; line-height: 1.6; }
.button {
  padding: 0.75rem 2rem; border-radius: 8px; border: none;
  background: #4a9eff; color: white; font-size: 1rem;
  cursor: pointer; transition: background 0.2s;
}
.button:hover { background: #3a8eef; }
```

- [ ] **Step 5: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add frontend/src/components/AdaptiveQuestion.tsx frontend/src/components/AdaptiveQuestion.module.css frontend/src/components/ProfileSummary.tsx frontend/src/components/ProfileSummary.module.css
git commit -m "feat: add AdaptiveQuestion and ProfileSummary frontend components"
```

---

## Task 13: Frontend — CheckInCard + EnergyReport Components

**Files:**
- Create: `frontend/src/components/CheckInCard.tsx`
- Create: `frontend/src/components/CheckInCard.module.css`
- Create: `frontend/src/components/EnergyReport.tsx`
- Create: `frontend/src/components/EnergyReport.module.css`

- [ ] **Step 1: Create CheckInCard component**

```tsx
// frontend/src/components/CheckInCard.tsx
import { useState, useEffect } from 'react';
import styles from './CheckInCard.module.css';

interface Props {
  question: string;
  options: string[];
  parameter: string;
  onAnswer: (parameter: string, answer: string) => void;
  onDismiss: () => void;
}

export default function CheckInCard({ question, options, parameter, onAnswer, onDismiss }: Props) {
  return (
    <div className={styles.overlay}>
      <div className={styles.card}>
        <h3 className={styles.title}>Weekly Check-in</h3>
        <p className={styles.question}>{question}</p>
        <div className={styles.options}>
          {options.map((opt) => (
            <button key={opt} className={styles.option} onClick={() => onAnswer(parameter, opt)}>
              {opt}
            </button>
          ))}
        </div>
        <button className={styles.dismiss} onClick={onDismiss}>Skip this week</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create CheckInCard CSS**

```css
/* frontend/src/components/CheckInCard.module.css */
.overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.7); display: flex;
  align-items: center; justify-content: center; z-index: 1000;
}
.card {
  background: #1a1a1a; border-radius: 16px; padding: 2rem;
  max-width: 420px; width: 90%; display: flex;
  flex-direction: column; gap: 1rem;
}
.title { font-size: 0.85rem; color: #666; text-transform: uppercase; letter-spacing: 0.05em; }
.question { font-size: 1.1rem; color: #e0e0e0; line-height: 1.5; }
.options { display: flex; flex-direction: column; gap: 0.5rem; }
.option {
  padding: 0.75rem; border-radius: 8px; border: 1px solid #333;
  background: transparent; color: #e0e0e0; cursor: pointer;
  text-align: center; transition: all 0.2s;
}
.option:hover { border-color: #4a9eff; background: #1a2a3a; }
.dismiss { background: none; border: none; color: #555; cursor: pointer; padding: 0.5rem; font-size: 0.85rem; }
.dismiss:hover { color: #888; }
```

- [ ] **Step 3: Create EnergyReport component**

```tsx
// frontend/src/components/EnergyReport.tsx
import { useState, useEffect } from 'react';
import styles from './EnergyReport.module.css';

interface Props {
  blockId: string;
  onReport: (blockId: string, level: string) => void;
  onDismiss: () => void;
}

export default function EnergyReport({ blockId, onReport, onDismiss }: Props) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      onDismiss();
    }, 10000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  if (!visible) return null;

  return (
    <div className={styles.container}>
      <span className={styles.label}>How do you feel?</span>
      <div className={styles.buttons}>
        <button className={styles.btn} onClick={() => onReport(blockId, 'low')}>Low</button>
        <button className={styles.btn} onClick={() => onReport(blockId, 'ok')}>OK</button>
        <button className={styles.btn} onClick={() => onReport(blockId, 'great')}>Great</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create EnergyReport CSS**

```css
/* frontend/src/components/EnergyReport.module.css */
.container {
  position: fixed; bottom: 1.5rem; right: 1.5rem;
  background: #1a1a1a; border-radius: 12px; padding: 1rem 1.25rem;
  display: flex; align-items: center; gap: 1rem;
  border: 1px solid #333; z-index: 900;
  animation: slideIn 0.3s ease-out;
}
@keyframes slideIn { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
.label { font-size: 0.9rem; color: #aaa; }
.buttons { display: flex; gap: 0.5rem; }
.btn {
  padding: 0.4rem 0.8rem; border-radius: 6px; border: 1px solid #444;
  background: transparent; color: #e0e0e0; cursor: pointer;
  font-size: 0.85rem; transition: all 0.2s;
}
.btn:hover { border-color: #4a9eff; background: #1a2a3a; }
```

- [ ] **Step 5: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add frontend/src/components/CheckInCard.tsx frontend/src/components/CheckInCard.module.css frontend/src/components/EnergyReport.tsx frontend/src/components/EnergyReport.module.css
git commit -m "feat: add CheckInCard and EnergyReport frontend components"
```

---

## Task 14: Frontend — Update API Client + Onboarding Page

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/app/onboarding/page.tsx:1-294`

- [ ] **Step 1: Add new API functions to api.ts**

Add to `frontend/src/lib/api.ts`:

```typescript
const API_BASE = 'http://localhost:8000';

export async function selectRole(role: string) {
  const res = await fetch(`${API_BASE}/api/onboarding/role`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role }),
  });
  return res.json();
}

export async function submitQuestionnaireAnswer(sessionId: string, questionId: string, answer: string) {
  const res = await fetch(`${API_BASE}/api/onboarding/questionnaire`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, question_id: questionId, answer }),
  });
  return res.json();
}

export async function getCheckIn() {
  const res = await fetch(`${API_BASE}/api/checkin/next`);
  return res.json();
}

export async function submitCheckIn(parameter: string, answer: string) {
  const res = await fetch(`${API_BASE}/api/checkin/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parameter, answer }),
  });
  return res.json();
}

export async function submitEnergyReport(blockId: string, level: string) {
  const res = await fetch(`${API_BASE}/api/self-report/energy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ block_id: blockId, level }),
  });
  return res.json();
}

export async function updateBlockStatus(blockId: string, status: string) {
  const res = await fetch(`${API_BASE}/api/blocks/${blockId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  return res.json();
}
```

- [ ] **Step 2: Update onboarding page to include role + questionnaire phases**

Modify `frontend/src/app/onboarding/page.tsx`:

- Add `'role' | 'questionnaire' | 'summary'` to the phase type (line ~20 where phase state is defined)
- Change initial phase from `'init'` to `'role'`
- Add imports for `RoleSelector`, `AdaptiveQuestion`, `ProfileSummary`
- Add state variables: `selectedRole`, `questionnaireSessionId`, `currentQuestion`, `profileSummary`
- Add handlers: `handleRoleSelect`, `handleQuestionAnswer`, `handleSummaryContinue`
- Add phase rendering for `role`, `questionnaire`, `summary` before existing `form` phase

Key changes to the component:
```tsx
import RoleSelector from '@/components/RoleSelector';
import AdaptiveQuestion from '@/components/AdaptiveQuestion';
import ProfileSummary from '@/components/ProfileSummary';
import { selectRole, submitQuestionnaireAnswer } from '@/lib/api';

// Add to state:
const [selectedRole, setSelectedRole] = useState<string | null>(null);
const [sessionId, setSessionId] = useState<string | null>(null);
const [currentQuestion, setCurrentQuestion] = useState<any>(null);
const [summary, setSummary] = useState<string | null>(null);

// Phase starts at 'role' instead of 'init'
const [phase, setPhase] = useState<'role' | 'questionnaire' | 'summary' | 'form' | 'theme' | 'chat' | 'preview'>('role');

// Handlers:
const handleRoleSelect = async (role: string) => {
  setSelectedRole(role);
  const data = await selectRole(role);
  setSessionId(data.session_id);
  setCurrentQuestion(data.next_question);
  setPhase('questionnaire');
};

const handleQuestionAnswer = async (questionId: string, answer: string) => {
  if (!sessionId) return;
  const data = await submitQuestionnaireAnswer(sessionId, questionId, answer);
  if (data.next_question) {
    setCurrentQuestion(data.next_question);
  } else {
    setSummary(data.summary);
    setPhase('summary');
  }
};

const handleSummaryContinue = () => setPhase('form');

// Render phases:
{phase === 'role' && <RoleSelector onSelect={handleRoleSelect} selected={selectedRole} />}
{phase === 'questionnaire' && currentQuestion && <AdaptiveQuestion question={currentQuestion} onAnswer={handleQuestionAnswer} />}
{phase === 'summary' && summary && <ProfileSummary summary={summary} onContinue={handleSummaryContinue} />}
```

- [ ] **Step 3: Verify frontend builds**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/frontend" && npx next build 2>&1 | tail -5`
Expected: Build succeeds or shows only minor warnings (not errors)

- [ ] **Step 4: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add frontend/src/lib/api.ts frontend/src/app/onboarding/page.tsx
git commit -m "feat: integrate role selection and adaptive questionnaire into onboarding flow"
```

---

## Task 15: Integration — Hook BehavioralTracker into Existing Endpoints

**Files:**
- Modify: `backend/app/api/intents.py:147-261` — add tracking after block creation
- Modify: `backend/app/api/adjust.py:1-91` — add tracking on reschedule

- [ ] **Step 1: Add tracking hook to intents.py**

After a block is created in the `parse` endpoint (~line 240-250), add:
```python
from app.services.behavioral_tracker import BehavioralTracker

_tracker = BehavioralTracker()

# After block is created and added to user_blocks:
# tracker.on_self_scheduled(beliefs, chosen_hour, duration_minutes)
# TODO: load user beliefs from DB, update, and persist
```

- [ ] **Step 2: Add tracking hook to adjust.py**

In the `disruption` endpoint, after a block is rescheduled, add:
```python
from app.services.behavioral_tracker import BehavioralTracker

_tracker = BehavioralTracker()

# After block is moved:
# tracker.on_reschedule(beliefs, original_hour, new_hour)
# TODO: load user beliefs from DB, update, and persist
```

- [ ] **Step 3: Commit**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add backend/app/api/intents.py backend/app/api/adjust.py
git commit -m "feat: add behavioral tracking hooks to intent parsing and schedule adjustment"
```

---

## Task 16: Run Full Test Suite + Final Verification

**Files:** None new — verification only.

- [ ] **Step 1: Run all backend tests**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && python -m pytest tests/ -v`
Expected: All tests pass (35+ tests across 8 test files)

- [ ] **Step 2: Verify backend starts without errors**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/backend" && timeout 5 python -m uvicorn app.main:app --port 8001 2>&1 || true`
Expected: Server starts, shows `Uvicorn running on http://0.0.0.0:8001`

- [ ] **Step 3: Verify frontend builds**

Run: `cd "/Users/amitbagra/Desktop/AI timeboxing/frontend" && npx next build 2>&1 | tail -10`
Expected: Build succeeds

- [ ] **Step 4: Final commit with all tests green**

```bash
cd "/Users/amitbagra/Desktop/AI timeboxing"
git add -A
git status
# Only commit if there are uncommitted changes
git commit -m "chore: final verification — all tests passing, both services start clean"
```
