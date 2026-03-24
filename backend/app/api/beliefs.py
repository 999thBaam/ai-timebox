from fastapi import APIRouter
from app.services.belief_store import get_beliefs as get_stored_beliefs

router = APIRouter(prefix="/api/beliefs", tags=["beliefs"])

@router.get("")
async def get_beliefs():
    beliefs = get_stored_beliefs() or {}
    return {
        "beliefs": [
            {"parameter": p.value, "value": b.belief_value, "confidence": b.confidence}
            for p, b in beliefs.items()
        ]
    }
