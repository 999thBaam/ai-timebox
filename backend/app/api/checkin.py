from fastapi import APIRouter, Request
from starlette.responses import JSONResponse
from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief
from app.services.checkin_generator import CheckInGenerator

router = APIRouter(prefix="/api/checkin", tags=["checkin"])
_checkin_generator = CheckInGenerator()


@router.get("/next")
async def get_next_checkin():
    return {"skip": True, "message": "No profile set up yet."}


@router.post("/answer")
async def submit_checkin_answer(request: Request):
    body = await request.json()
    return {"updated": True, "parameter": body.get("parameter")}
