from __future__ import annotations
"""Intent parsing and hypothesis endpoints."""
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.human_state import HumanState
from app.models.safety_policy import SafetyPolicy
from app.models.timeline import ScheduledBlock
from app.services import (
    get_llm_provider,
    build_hypothesis,
    resolve_unknown,
    evaluate_question_policy,
    plan,
)
from app.services.behavioral_tracker import BehavioralTracker
from app.services.belief_store import get_beliefs, update_beliefs
_tracker = BehavioralTracker()

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class IntentRequest(BaseModel):
    """User input to be parsed into an intent hypothesis."""
    user_id: UUID
    raw_input: str


class QuestionOption(BaseModel):
    """A single option for a clarifying question."""
    value: str
    label: str


class QuestionResponse(BaseModel):
    """Response when a clarifying question is needed."""
    hypothesis_id: UUID
    question: str
    options: List[QuestionOption]
    context: str


class ScheduledBlockResponse(BaseModel):
    """A scheduled block in the timeline."""
    id: UUID
    start_time: str
    end_time: str
    goal: str
    buffer_before_minutes: int
    buffer_after_minutes: int


class SuccessResponse(BaseModel):
    """Response when intent is successfully scheduled."""
    hypothesis_id: UUID
    scheduled: ScheduledBlockResponse
    explanation: str
    undo_id: UUID


class IntentResponse(BaseModel):
    """Union response - either a question or success."""
    type: str  # "question" | "success" | "failure"
    question: Optional[QuestionResponse] = None
    success: Optional[SuccessResponse] = None
    failure_reason: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# IN-MEMORY STORES (For MVP - replace with DB in production)
# ═══════════════════════════════════════════════════════════════════════════════

# Temporary in-memory storage for MVP
_hypotheses: dict[UUID, dict] = {}
_user_states: dict[UUID, HumanState] = {}
_user_blocks: dict[UUID, list[ScheduledBlock]] = {}
_timeline_changes: dict[UUID, dict] = {}


def get_user_state(user_id: UUID) -> HumanState:
    """Get or create user state."""
    if user_id not in _user_states:
        _user_states[user_id] = HumanState(
            user_id=user_id,
            updated_at=datetime.now(),
        )
    return _user_states[user_id]


def get_user_blocks(user_id: UUID) -> list[ScheduledBlock]:
    """Get user's scheduled blocks."""
    return _user_blocks.get(user_id, [])


def get_user_policies(user_id: UUID) -> list[SafetyPolicy]:
    """Get user's safety policies (default set for MVP)."""
    # Default policies for all users
    from app.models.safety_policy import ActivationCondition, PolicySource, DecayCurve
    
    return [
        SafetyPolicy(
            user_id=user_id,
            name="Prevent Cognitive Overload",
            source=PolicySource.QUESTIONNAIRE,
            protected_dimension="cognitive_load",
            activation_condition=ActivationCondition(
                metric="cognitive_load",
                operator=">",
                threshold=0.8,
            ),
            action={"type": "INSERT_BUFFER", "minutes": 15},
            initial_strength=1.0,
            current_strength=1.0,
            decay_curve=DecayCurve.EXPONENTIAL,
            decay_rate=0.02,
        ),
        SafetyPolicy(
            user_id=user_id,
            name="Protect Low Energy",
            source=PolicySource.QUESTIONNAIRE,
            protected_dimension="confidence",
            activation_condition=ActivationCondition(
                metric="energy_level",
                operator="<",
                threshold=0.2,
            ),
            action={"type": "BLOCK_DEEP_WORK"},
            initial_strength=1.0,
            current_strength=1.0,
            decay_curve=DecayCurve.LINEAR,
            decay_rate=0.01,
        ),
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/parse", response_model=IntentResponse)
async def parse_intent(request: IntentRequest) -> IntentResponse:
    """
    Parse user input into an intent hypothesis.
    
    This is the main entry point for the AI Timebox system:
    1. Parses natural language via LLM
    2. Builds IntentHypothesis (IHF 2.0)
    3. Evaluates Question Policy
    4. Either asks a clarifying question OR proceeds to planning
    """
    # Step 1: Parse via LLM
    llm = get_llm_provider()
    parsed = await llm.parse_intent(request.raw_input)

    # Step 2: Build full hypothesis
    hypothesis = build_hypothesis(parsed, request.raw_input)

    # Store hypothesis
    _hypotheses[hypothesis.id] = {
        "hypothesis": hypothesis,
        "user_id": request.user_id,
    }

    # Step 3: Get user context
    state = get_user_state(request.user_id)
    policies = get_user_policies(request.user_id)

    # Step 4: Question Policy
    decision = evaluate_question_policy(
        hypothesis=hypothesis,
        state=state,
        policies=policies,
        recent_questions=0,
    )

    if decision.should_ask and decision.question:
        return IntentResponse(
            type="question",
            question=QuestionResponse(
                hypothesis_id=hypothesis.id,
                question=decision.question.text,
                options=[
                    QuestionOption(value=v, label=l)
                    for v, l in decision.question.options
                ],
                context=decision.question.context,
            ),
        )

    # Step 5: Apply assumptions if any
    if decision.assumptions:
        for assumption in decision.assumptions:
            hypothesis = resolve_unknown(
                hypothesis,
                assumption.parameter,
                assumption.assumed_value,
            )
        _hypotheses[hypothesis.id]["hypothesis"] = hypothesis

    # Step 6: Plan
    existing_blocks = get_user_blocks(request.user_id)
    result = await plan(
        user_id=request.user_id,
        hypothesis=hypothesis,
        current_state=state,
        existing_blocks=existing_blocks,
        policies=policies,
    )

    if not result.success or not result.selected:
        return IntentResponse(
            type="failure",
            failure_reason="Could not find a suitable time slot. " + 
                          (result.explanation_facts.reasons[0] if result.explanation_facts.reasons else ""),
        )

    # Step 7: Commit (store block)
    block = result.selected.blocks[0]
    if request.user_id not in _user_blocks:
        _user_blocks[request.user_id] = []
    _user_blocks[request.user_id].append(block)

    # Create undo point
    change_id = uuid4()
    _timeline_changes[change_id] = {
        "user_id": request.user_id,
        "block_id": block.id,
        "type": "ADD",
    }

    # Step 8: Generate explanation text
    explanation_text = result.explanation_text
    if not explanation_text:
        # Generate via LLM
        explanation_text = await llm.verbalize_explanation(
            result.explanation_facts.to_dict()
        )

    return IntentResponse(
        type="success",
        success=SuccessResponse(
            hypothesis_id=hypothesis.id,
            scheduled=ScheduledBlockResponse(
                id=block.id,
                start_time=block.start_time.isoformat(),
                end_time=block.end_time.isoformat(),
                goal=block.goal,
                buffer_before_minutes=block.buffer_before_minutes,
                buffer_after_minutes=block.buffer_after_minutes,
            ),
            explanation=explanation_text,
            undo_id=change_id,
        ),
    )


class AnswerRequest(BaseModel):
    """User's answer to a clarifying question."""
    hypothesis_id: UUID
    parameter: str
    value: str


@router.post("/answer", response_model=IntentResponse)
async def answer_question(request: AnswerRequest) -> IntentResponse:
    """
    Process user's answer to a clarifying question.
    
    Updates the hypothesis with the provided answer and
    continues the intent processing flow.
    """
    # Get stored hypothesis
    stored = _hypotheses.get(request.hypothesis_id)
    if not stored:
        return IntentResponse(
            type="failure",
            failure_reason="Hypothesis not found. Please start over.",
        )

    hypothesis = stored["hypothesis"]
    user_id = stored["user_id"]

    # Resolve the unknown
    hypothesis = resolve_unknown(hypothesis, request.parameter, request.value)
    _hypotheses[request.hypothesis_id]["hypothesis"] = hypothesis

    # Continue with planning
    state = get_user_state(user_id)
    policies = get_user_policies(user_id)
    existing_blocks = get_user_blocks(user_id)

    result = await plan(
        user_id=user_id,
        hypothesis=hypothesis,
        current_state=state,
        existing_blocks=existing_blocks,
        policies=policies,
    )

    if not result.success or not result.selected:
        return IntentResponse(
            type="failure",
            failure_reason="Could not find a suitable time slot.",
        )

    # Commit
    block = result.selected.blocks[0]
    if user_id not in _user_blocks:
        _user_blocks[user_id] = []
    _user_blocks[user_id].append(block)

    change_id = uuid4()
    _timeline_changes[change_id] = {
        "user_id": user_id,
        "block_id": block.id,
        "type": "ADD",
    }

    # Generate explanation
    llm = get_llm_provider()
    explanation_text = await llm.verbalize_explanation(
        result.explanation_facts.to_dict()
    )

    return IntentResponse(
        type="success",
        success=SuccessResponse(
            hypothesis_id=hypothesis.id,
            scheduled=ScheduledBlockResponse(
                id=block.id,
                start_time=block.start_time.isoformat(),
                end_time=block.end_time.isoformat(),
                goal=block.goal,
                buffer_before_minutes=block.buffer_before_minutes,
                buffer_after_minutes=block.buffer_after_minutes,
            ),
            explanation=explanation_text,
            undo_id=change_id,
        ),
    )
