from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/self-report", tags=["self-report"])


@router.post("/energy")
async def submit_energy_report(request: Request):
    body = await request.json()
    level = body.get("level")
    block_id = body.get("block_id")
    if level not in ("low", "ok", "great"):
        return JSONResponse(status_code=400, content={"error": f"Invalid level: {level}"})
    return {"recorded": True, "level": level, "block_id": block_id}
