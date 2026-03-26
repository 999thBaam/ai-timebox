"""Onboarding API endpoints."""
from __future__ import annotations

import uuid as uuid_mod
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette.responses import JSONResponse

from app.models.role_profile import RoleType
from app.services.adaptive_questionnaire import AdaptiveQuestionnaire
from app.services.questionnaire import (
    get_onboarding_questions,
    process_onboarding,
)

router = APIRouter()

# In-memory session storage for adaptive questionnaires
_questionnaire_sessions: dict = {}


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


# --- Conversational Onboarding (Phase 5) ---

from datetime import datetime, time
from app.models.onboarding import UserProfile
from app.services.onboarding_orchestrator import onboarding_orchestrator
from app.services.schedule_generator import schedule_generator
from app.models.timeline import ScheduledBlock


class CreateSessionRequest(BaseModel):
    user_id: UUID


class CreateSessionResponse(BaseModel):
    session_id: UUID
    message: str


class UpdateProfileRequest(BaseModel):
    session_id: UUID
    wake_time: str  # HH:MM
    sleep_time: str
    work_start: str
    work_end: str
    fixed_commitments: List[dict] = []


class SetThemeRequest(BaseModel):
    session_id: UUID
    theme: str


class ChatRequest(BaseModel):
    session_id: UUID
    message: str


class ChatResponse(BaseModel):
    message: str
    should_stop: bool
    extracted_tasks_count: int


class GenerateScheduleRequest(BaseModel):
    session_id: UUID
    date: str  # YYYY-MM-DD


class BlockResponse(BaseModel):
    id: UUID
    intent_id: Optional[UUID] = None
    start_time: datetime
    end_time: datetime
    goal: str
    activity_nature: str
    is_locked: bool

class GeneratedScheduleResponse(BaseModel):
    blocks: List[BlockResponse]
    confidence: float
    has_overflow: bool
    overflow_count: int


@router.post("/generate", response_model=GeneratedScheduleResponse)
async def generate_schedule(request: GenerateScheduleRequest) -> GeneratedScheduleResponse:
    """Generate the schedule based on gathered intents."""
    session = onboarding_orchestrator.get_session(request.session_id)
    if not session:
        raise ValueError("Session not found")
        
    target_date = datetime.strptime(request.date, "%Y-%m-%d")
    schedule = schedule_generator.generate(session, target_date)
    
    return GeneratedScheduleResponse(
        blocks=[
            BlockResponse(
                id=b.id, 
                intent_id=b.intent_id,
                start_time=b.start_time,
                end_time=b.end_time,
                goal=b.goal,
                activity_nature=b.activity_nature,
                is_locked=b.is_locked,
            )
            for b in schedule.blocks
        ],
        confidence=schedule.confidence,
        has_overflow=schedule.has_overflow,
        overflow_count=len(schedule.overflow_tasks)
    )


@router.post("/session", response_model=CreateSessionResponse)
async def start_session(request: CreateSessionRequest) -> CreateSessionResponse:
    """Start a new conversational onboarding session."""
    session = await onboarding_orchestrator.start_session(request.user_id)
    return CreateSessionResponse(
        session_id=session.id,
        message="Let's set up your cognitive profile. First, tell me about your typical day."
    )


@router.post("/profile", response_model=CreateSessionResponse)
async def set_profile(request: UpdateProfileRequest) -> CreateSessionResponse:
    """Set the user's time constraints (Smart Forms)."""
    # Parse times
    def parse_time(t_str):
        return datetime.strptime(t_str, "%H:%M").time()

    profile = UserProfile(
        user_id=UUID("00000000-0000-0000-0000-000000000000"), # Placeholder user
        wake_time=parse_time(request.wake_time),
        sleep_time=parse_time(request.sleep_time),
        work_start=parse_time(request.work_start),
        work_end=parse_time(request.work_end),
        fixed_commitments=request.fixed_commitments
    )
    
    await onboarding_orchestrator.set_profile(request.session_id, profile)
    
    return CreateSessionResponse(
        session_id=request.session_id,
        message="Got it. Now, what is your main THEME for this week?"
    )


@router.post("/theme", response_model=ChatResponse)
async def set_theme(request: SetThemeRequest) -> ChatResponse:
    """Set the theme and start task extraction."""
    session = await onboarding_orchestrator.set_theme(request.session_id, request.theme)
    
    return ChatResponse(
        message=f"Got it — your week is about: {request.theme}\n\nNow just list what you need to get done. One task per message, like:\n\n• \"Fix the login bug\"\n• \"Write 3 Instagram posts\"\n• \"Call the designer\"\n\nType 'done' when you've added everything.",
        should_stop=False,
        extracted_tasks_count=0
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat message and extract tasks."""
    session, response = await onboarding_orchestrator.process_message(
        request.session_id, 
        request.message
    )
    
    return ChatResponse(
        message=response,
        should_stop=session.should_stop(),
        extracted_tasks_count=len(session.extracted_tasks)
    )


# --- Adaptive Role Selection & Questionnaire (Phase 6) ---


@router.post("/role")
async def select_role(request: Request):
    body = await request.json()
    role_str = body.get("role", "").lower()
    try:
        role = RoleType(role_str)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": f"Invalid role: {role_str}"})
    aq = AdaptiveQuestionnaire(role)
    session_id = str(uuid_mod.uuid4())
    _questionnaire_sessions[session_id] = aq
    first_question = aq.get_next_question()
    return {"session_id": session_id, "next_question": first_question}


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
        from app.services.belief_store import set_beliefs
        beliefs = aq.get_beliefs()
        set_beliefs(beliefs)
        summary = aq.get_summary()
        return {"next_question": None, "summary": summary, "beliefs_initialized": True}
    return {"next_question": next_q, "summary": None, "conflict": result["conflict"]}
