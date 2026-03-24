from fastapi import APIRouter, Request
from starlette.responses import JSONResponse
from app.models.role_profile import BeliefParameter
from app.services.checkin_generator import CheckInGenerator, QUESTION_TEMPLATES
from app.services.belief_store import get_beliefs, update_beliefs
from app.services.belief_updater import SignalType

router = APIRouter(prefix="/api/checkin", tags=["checkin"])
_checkin_generator = CheckInGenerator()

@router.get("/next")
async def get_next_checkin():
    beliefs = get_beliefs()
    if not beliefs:
        return {"skip": True, "message": "No profile set up yet."}
    return _checkin_generator.generate(beliefs, week_data={})

@router.post("/answer")
async def submit_checkin_answer(request: Request):
    body = await request.json()
    parameter = body.get("parameter")
    answer = body.get("answer")
    beliefs = get_beliefs()
    if not beliefs:
        return JSONResponse(status_code=404, content={"error": "No beliefs found"})
    param_enum = BeliefParameter(parameter)
    template = QUESTION_TEMPLATES.get(param_enum)
    if template and answer in template["encoding"]:
        encoded = template["encoding"][answer]
        if param_enum == BeliefParameter.DEEP_WORK_TOLERANCE:
            encoded = beliefs[param_enum].belief_value * encoded
        belief = beliefs[param_enum].update(encoded, SignalType.ENERGY_SELF_REPORT.weight)
        update_beliefs({param_enum: belief})
    return {"updated": True, "parameter": parameter}
