from datetime import datetime
from fastapi import APIRouter, Request
from starlette.responses import JSONResponse
from app.services.belief_store import get_beliefs, update_beliefs
from app.services.behavioral_tracker import BehavioralTracker

router = APIRouter(prefix="/api/self-report", tags=["self-report"])
_tracker = BehavioralTracker()

@router.post("/energy")
async def submit_energy_report(request: Request):
    body = await request.json()
    level = body.get("level")
    if level not in ("low", "ok", "great"):
        return JSONResponse(status_code=400, content={"error": f"Invalid level: {level}"})
    current_hour = datetime.now().hour + datetime.now().minute / 60.0
    beliefs = get_beliefs()
    if beliefs:
        updated = _tracker.on_energy_report(beliefs, current_hour, level)
        update_beliefs(updated)
    return {"recorded": True, "level": level}
