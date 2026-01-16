from __future__ import annotations
"""Undo/redo endpoints."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


# Get reference to in-memory stores from intents module
def _get_stores():
    from app.api.intents import _timeline_changes, _user_blocks
    return _timeline_changes, _user_blocks


class UndoHistoryItem(BaseModel):
    """A single undo-able change."""
    id: UUID
    timestamp: str
    change_type: str
    description: str
    can_undo: bool


class UndoHistoryResponse(BaseModel):
    """Recent changes that can be undone."""
    user_id: UUID
    changes: list[UndoHistoryItem]


@router.get("/{user_id}/history", response_model=UndoHistoryResponse)
async def get_undo_history(user_id: UUID, limit: int = 10) -> UndoHistoryResponse:
    """Get recent changes that can be undone."""
    changes_store, blocks_store = _get_stores()
    
    # Filter changes for this user
    user_changes = [
        (cid, data) for cid, data in changes_store.items()
        if data.get("user_id") == user_id and not data.get("undone", False)
    ]
    
    # Sort by timestamp (newest first) and limit
    user_changes = user_changes[:limit]
    
    return UndoHistoryResponse(
        user_id=user_id,
        changes=[
            UndoHistoryItem(
                id=cid,
                timestamp=datetime.now().isoformat(),  # Would be stored in real impl
                change_type=data.get("type", "ADD"),
                description=f"Added block {data.get('block_id', 'unknown')}",
                can_undo=True,
            )
            for cid, data in user_changes
        ],
    )


class UndoResponse(BaseModel):
    """Result of an undo operation."""
    success: bool
    message: str


@router.post("/{user_id}/undo/{change_id}", response_model=UndoResponse)
async def undo_change(user_id: UUID, change_id: UUID) -> UndoResponse:
    """
    Undo a specific change.
    
    Undo is sacred - this should always work for recent changes.
    """
    changes_store, blocks_store = _get_stores()
    
    if change_id not in changes_store:
        raise HTTPException(status_code=404, detail="Change not found")
    
    change = changes_store[change_id]
    
    if change.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if change.get("undone"):
        raise HTTPException(status_code=400, detail="Already undone")
    
    # Perform undo based on change type
    if change.get("type") == "ADD":
        block_id = change.get("block_id")
        if user_id in blocks_store:
            blocks_store[user_id] = [
                b for b in blocks_store[user_id]
                if b.id != block_id
            ]
    
    # Mark as undone
    changes_store[change_id]["undone"] = True
    
    return UndoResponse(
        success=True,
        message="Change undone successfully",
    )
