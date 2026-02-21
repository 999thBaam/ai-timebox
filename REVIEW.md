# AI Timebox - Project Review

## Idea Assessment

The concept is genuinely compelling. A "cognitive calendar" that models human state
(energy, cognitive load, fragility) rather than just time availability addresses a real
gap in the productivity tool market. Most scheduling tools treat people as containers
with empty time slots. This project treats them as dynamic systems with limited cognitive
bandwidth.

The philosophical framing -- "not productivity software, cognitive infrastructure" -- is a
strong differentiator. The theoretical underpinnings are sound: treating user input as
hypotheses (IHF 2.0), using VOI/COI analysis to decide when to ask questions, and
modeling safety policies with natural decay are all well-designed concepts.

**Main risk**: The system is heavily dependent on the quality of the cognitive state model,
which currently relies entirely on (a) self-reported onboarding answers and (b) static
simulation parameters. Without a behavioral learning feedback loop, the model will diverge
from reality quickly.

---

## Architecture Strengths

1. **Rich domain model** -- `HumanState` with 7 dimensions is well-thought-out.
   The `safe_load_capacity` property and `with_decay()` method show careful design.

2. **Safety Policies with decay** -- Policies weaken over time via configurable curves,
   and can be overridden by behavioral evidence.

3. **VOI/COI question policy** -- The decision to ask vs. assume is driven by a proper
   cost-benefit framework, not arbitrary heuristics.

4. **Multi-candidate planner** -- Generates, simulates, safety-checks, and scores
   multiple candidates before selection.

5. **Explanation architecture** -- Planner generates structured facts; LLM only
   verbalizes them. Prevents hallucinated explanations.

6. **Undo as first-class concern** -- Reversibility designed in from the start.

---

## Critical Issues

### 1. No persistence (in-memory storage only)
Despite having full ORM models, Alembic migrations, and async PostgreSQL configuration,
all API endpoints use in-memory Python dicts. All data is lost on server restart.

### 2. No frontend
The `frontend/` directory is empty.

### 3. Zero tests
No test files exist despite `pytest` being in dev dependencies. The domain models are
highly testable pure functions.

### 4. No authentication
User identity is passed as `user_id` in request bodies. Any client can act as any user.

### 5. CORS wildcard negates security
`allow_origins` includes both specific origins and `"*"`, which makes the specific
origins meaningless. Combined with `allow_credentials=True`, this is a security issue.

### 6. `assert` for validation
`assert` is used for input validation in domain models. Python assertions can be disabled
with `python -O`, silently removing all validation. Should use `ValueError`.

### 7. Naive `datetime.now()` throughout
No timezone info on timestamps. Will produce incorrect results in non-local-timezone
deployments and makes cross-timezone usage impossible.

---

## Architectural Issues

- **Onboarding doesn't persist** -- Computes calibrated state but doesn't store it
- **Cross-module state coupling** -- Multiple API modules import private dicts from `intents.py`
- **Safety check uses hardcoded mock values** -- Hardcoded emotional_load, confidence, etc.
- **Redis configured but unused** -- In docker-compose and config but never used
- **LLM provider only implements OpenAI** -- Despite claiming provider-agnosticism
- **Duplicate policy definitions** -- Default policies defined in two places

---

## Suggested Improvements (Prioritized)

### High Priority
1. Wire up database persistence (ORM models and sessions are already built)
2. Add tests for domain core (state decay, safety policies, VOI/COI, planner)
3. Build a minimal frontend (text input, timeline display, undo button)
4. Connect onboarding to state stores
5. Replace `assert` with `ValueError` in domain models

### Medium Priority
6. Add authentication (JWT or session-based)
7. Use timezone-aware datetimes everywhere
8. Extract shared state into a repository layer
9. Add error handling for LLM calls
10. Fix CORS configuration

### Lower Priority
11. Add behavioral learning (track task completion, calibrate model over time)
12. Multi-day planning support
13. Recurring events
14. Calendar integration (Google Calendar / Outlook)
15. Implement safety policy action types in the planner

---

## Code Quality Summary

| Dimension | Rating | Notes |
|---|---|---|
| Domain modeling | Strong | Rich, well-structured with meaningful business logic |
| Architecture | Decent | Clean separation, but persistence layer disconnected |
| API design | Good | RESTful, well-structured request/response models |
| Code style | Good | Consistent, well-commented, good use of dataclasses |
| Testing | Absent | No tests at all |
| Security | Weak | No auth, CORS wildcard, assert-based validation |
| Production readiness | Low | In-memory storage, no frontend, no error handling |
| Completeness | ~30% | Backend skeleton only; core ideas present but unconnected |

---

## Bottom Line

The idea is strong and the domain modeling shows genuine depth of thought. The IHF 2.0
framework, safety policies with decay, and VOI/COI question policy reflect careful
consideration of what "humane scheduling" actually means.

The implementation is at an early prototype stage. The most impactful next steps are:
wire up persistence, add tests for the domain core, build a minimal UI, and close the
gap between onboarding and the rest of the system. The theoretical framework is the hard
part and it's well-done -- the engineering work to make it functional is largely mechanical.
