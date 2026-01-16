from __future__ import annotations
"""Human state endpoints (read-only for users)."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


# Get reference to in-memory stores from intents module
def _get_stores():
    from app.api.intents import _user_states
    return _user_states


class HumanStateResponse(BaseModel):
    """
    User's current cognitive state.
    
    Note: This is intentionally limited exposure.
    Full state is internal; users see simplified version.
    """
    user_id: UUID
    updated_at: str
    energy_level: str  # "low" | "medium" | "high"
    load_status: str   # "light" | "moderate" | "heavy"
    recommendation: str


@router.get("/{user_id}", response_model=HumanStateResponse)
async def get_state_summary(user_id: UUID) -> HumanStateResponse:
    """
    Get simplified view of user's current cognitive state.
    
    This does NOT expose raw state values (those are internal).
    Instead, provides actionable, human-friendly guidance.
    """
    states_store = _get_stores()
    
    from app.models.human_state import HumanState
    
    if user_id not in states_store:
        # Create default state
        states_store[user_id] = HumanState(
            user_id=user_id,
            updated_at=datetime.now(),
        )
    
    state = states_store[user_id]
    
    # Apply decay to get current state
    current = state.with_decay(datetime.now())
    
    # Get simplified view
    simplified = current.to_simplified_view()
    
    return HumanStateResponse(
        user_id=user_id,
        updated_at=current.updated_at.isoformat(),
        energy_level=simplified["energy_level"],
        load_status=simplified["load_status"],
        recommendation=simplified["recommendation"],
    )
