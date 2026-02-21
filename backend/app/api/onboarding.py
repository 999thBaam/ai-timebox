"""Onboarding API endpoints."""
from __future__ import annotations

from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.questionnaire import (
    get_onboarding_questions,
    process_onboarding,
)

router = APIRouter()


class QuestionOptionResponse(BaseModel):
    value: str
    label: str


class OnboardingQuestionResponse(BaseModel):
    id: str
    category: str
    question: str
    context: str
    options: List[QuestionOptionResponse]
    required: bool


class OnboardingQuestionsResponse(BaseModel):
    questions: List[OnboardingQuestionResponse]


@router.get("/questions", response_model=OnboardingQuestionsResponse)
async def get_questions() -> OnboardingQuestionsResponse:
    """Get onboarding questionnaire."""
    questions = get_onboarding_questions()
    return OnboardingQuestionsResponse(
        questions=[
            OnboardingQuestionResponse(
                id=q["id"],
                category=q["category"],
                question=q["question"],
                context=q["context"],
                options=[
                    QuestionOptionResponse(value=o["value"], label=o["label"])
                    for o in q["options"]
                ],
                required=q["required"],
            )
            for q in questions
        ]
    )


class OnboardingSubmitRequest(BaseModel):
    user_id: UUID
    answers: Dict[str, str]


class PolicyResponse(BaseModel):
    id: UUID
    name: str
    protected_dimension: str


class StateResponse(BaseModel):
    energy_level: float
    cognitive_load: float
    fragility: float
    chaos_tolerance: float


class OnboardingResultResponse(BaseModel):
    success: bool
    state: StateResponse
    policies: List[PolicyResponse]
    message: str


@router.post("/submit", response_model=OnboardingResultResponse)
async def submit_onboarding(request: OnboardingSubmitRequest) -> OnboardingResultResponse:
    """
    Submit onboarding answers and get calibrated initial state.
    """
    state, policies = process_onboarding(request.user_id, request.answers)

    # Persist to in-memory store so intents/planning can use them
    from app.api.intents import _user_states, _user_policies
    _user_states[request.user_id] = state
    _user_policies[request.user_id] = policies

    return OnboardingResultResponse(
        success=True,
        state=StateResponse(
            energy_level=state.energy_level,
            cognitive_load=state.cognitive_load,
            fragility=state.fragility,
            chaos_tolerance=state.chaos_tolerance,
        ),
        policies=[
            PolicyResponse(
                id=p.id,
                name=p.name,
                protected_dimension=p.protected_dimension,
            )
            for p in policies
        ],
        message=f"Your cognitive profile has been calibrated. We created {len(policies)} protective policies based on your preferences.",
    )
