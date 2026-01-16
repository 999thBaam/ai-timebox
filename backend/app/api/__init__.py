from __future__ import annotations
"""API router aggregating all endpoints."""
from fastapi import APIRouter

from app.api import intents, timeline, state, undo, onboarding

router = APIRouter()

router.include_router(intents.router, prefix="/intents", tags=["intents"])
router.include_router(timeline.router, prefix="/timeline", tags=["timeline"])
router.include_router(state.router, prefix="/state", tags=["state"])
router.include_router(undo.router, prefix="/undo", tags=["undo"])
router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
