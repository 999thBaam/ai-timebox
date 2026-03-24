from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/api/blocks", tags=["blocks"])


@router.patch("/{block_id}/status")
async def update_block_status(block_id: str, request: Request):
    body = await request.json()
    new_status = body.get("status")
    valid = {"completed", "skipped", "partial", "rescheduled", "in_progress"}
    if new_status not in valid:
        return JSONResponse(status_code=400, content={"error": f"Invalid status: {new_status}"})
    return {"updated": True, "block_id": block_id, "status": new_status}
