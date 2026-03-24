"""Adjustment API endpoints."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.timeline import ScheduledBlock
from app.api.onboarding import BlockResponse, GeneratedScheduleResponse
from app.services.adjustment_orchestrator import adjustment_orchestrator, DisruptionType
from app.services.behavioral_tracker import BehavioralTracker
from app.services.belief_store import get_beliefs, update_beliefs
_tracker = BehavioralTracker()

router = APIRouter()


class DisruptionRequest(BaseModel):
    session_id: UUID
    current_schedule: List[BlockResponse] # Client sends current state
    disruption_type: DisruptionType
    details: dict


@router.post("/disruption", response_model=GeneratedScheduleResponse)
async def handle_disruption(request: DisruptionRequest) -> GeneratedScheduleResponse:
    """
    Handle a schedule disruption.
    """
    # Convert request models back to domain models
    # Note: BlockResponse has 'id' but ScheduledBlock needs converting
    current_schedule = []
    for b in request.current_schedule:
        # We need to reconstruct ScheduledBlock. 
        # For MVP, we might need a better way to hydrate this, or just map fields.
        # Assuming BlockResponse fields map 1:1 mostly.
        block = ScheduledBlock(
             # We need user_id, intent_id, etc. which might be missing in BlockResponse
             # Ideally we fetch from DB. For now, we rely on the session/generator to create new ones,
             # and we only strictly need start/end/nature for the "Available Slots" calculation.
             # However, AdjustmentOrchestrator._handle_overrun uses intent_id to filter tasks.
             # So we DO need intent_id in BlockResponse or fetch from DB.
             # For this prototype, let's assume client sends minimal needed 
             # and we might have issues if intent_id is missing.
             # Let's add intent_id to BlockResponse in onboarding.py if not there?
             # Actually BlockResponse has 'id'. Is that intent_id? 
             # In generate_schedule mapping: id=b.id.
             # ScheduledBlock.id is usually random UUID. intent_id is the task ID.
             # We need intent_id to filter completed tasks!
             
             # HACK: If we can't get intent_id, we can't filter safely. 
             # Let's just pass what we have and see.
             id=b.id,
             start_time=b.start_time,
             end_time=b.end_time,
             goal=b.goal,
             activity_nature=b.activity_nature,
             is_locked=b.is_locked,
             user_id=request.session_id, 
             intent_id=b.intent_id 
        )
        current_schedule.append(block)

    try:
        new_schedule = await adjustment_orchestrator.handle_disruption(
            request.session_id,
            current_schedule,
            request.disruption_type,
            request.details
        )
        
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
                for b in new_schedule.blocks
            ],
            confidence=new_schedule.confidence,
            has_overflow=new_schedule.has_overflow,
            overflow_count=len(new_schedule.overflow_tasks)
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
