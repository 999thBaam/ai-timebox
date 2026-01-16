from __future__ import annotations
"""Timeline management endpoints."""
from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


# Get reference to in-memory stores from intents module
def _get_stores():
    from app.api.intents import _user_blocks
    return _user_blocks


class TimelineBlockResponse(BaseModel):
    """A block in the user's timeline."""
    id: UUID
    intent_id: UUID
    start_time: str
    end_time: str
    goal: str
    activity_nature: str
    buffer_before_minutes: int
    buffer_after_minutes: int
    is_locked: bool


class TimelineResponse(BaseModel):
    """User's timeline for a given date range."""
    user_id: UUID
    date: str
    blocks: List[TimelineBlockResponse]


@router.get("/{user_id}", response_model=TimelineResponse)
async def get_timeline(
    user_id: UUID,
    target_date: Optional[date] = None,
) -> TimelineResponse:
    """
    Get user's timeline for a specific date.
    
    Defaults to today if no date provided.
    """
    blocks_store = _get_stores()
    target = target_date or date.today()
    
    user_blocks = blocks_store.get(user_id, [])
    
    # Filter to target date
    day_blocks = [
        b for b in user_blocks
        if b.start_time.date() == target
    ]
    
    # Sort by start time
    day_blocks.sort(key=lambda b: b.start_time)
    
    return TimelineResponse(
        user_id=user_id,
        date=target.isoformat(),
        blocks=[
            TimelineBlockResponse(
                id=b.id,
                intent_id=b.intent_id,
                start_time=b.start_time.isoformat(),
                end_time=b.end_time.isoformat(),
                goal=b.goal,
                activity_nature=b.activity_nature,
                buffer_before_minutes=b.buffer_before_minutes,
                buffer_after_minutes=b.buffer_after_minutes,
                is_locked=b.is_locked,
            )
            for b in day_blocks
        ],
    )


class LockBlockRequest(BaseModel):
    """Request to lock/unlock a block."""
    is_locked: bool


@router.patch("/{user_id}/blocks/{block_id}/lock", response_model=TimelineBlockResponse)
async def toggle_block_lock(
    user_id: UUID,
    block_id: UUID,
    request: LockBlockRequest,
) -> TimelineBlockResponse:
    """Lock or unlock a scheduled block."""
    blocks_store = _get_stores()
    user_blocks = blocks_store.get(user_id, [])
    
    for block in user_blocks:
        if block.id == block_id:
            block.is_locked = request.is_locked
            return TimelineBlockResponse(
                id=block.id,
                intent_id=block.intent_id,
                start_time=block.start_time.isoformat(),
                end_time=block.end_time.isoformat(),
                goal=block.goal,
                activity_nature=block.activity_nature,
                buffer_before_minutes=block.buffer_before_minutes,
                buffer_after_minutes=block.buffer_after_minutes,
                is_locked=block.is_locked,
            )
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Block not found")
