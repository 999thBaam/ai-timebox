from fastapi import APIRouter, Request
from starlette.responses import JSONResponse
from app.services.belief_store import get_beliefs, update_beliefs
from app.services.behavioral_tracker import BehavioralTracker

router = APIRouter(prefix="/api/blocks", tags=["blocks"])
_tracker = BehavioralTracker()

@router.patch("/{block_id}/status")
async def update_block_status(block_id: str, request: Request):
    body = await request.json()
    new_status = body.get("status")
    valid = {"completed", "skipped", "partial", "rescheduled", "in_progress"}
    if new_status not in valid:
        return JSONResponse(status_code=400, content={"error": f"Invalid status: {new_status}"})
    block_start_hour = body.get("block_start_hour", 12.0)
    block_duration_minutes = body.get("block_duration_minutes", 45.0)
    beliefs = get_beliefs()
    if beliefs and new_status in ("completed", "skipped", "partial"):
        updated = _tracker.on_block_status_change(beliefs, block_start_hour, block_duration_minutes, new_status)
        update_beliefs(updated)
    return {"updated": True, "block_id": block_id, "status": new_status}
