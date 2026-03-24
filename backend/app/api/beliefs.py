from fastapi import APIRouter

router = APIRouter(prefix="/api/beliefs", tags=["beliefs"])


@router.get("")
async def get_beliefs():
    return {"beliefs": []}
