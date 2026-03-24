from __future__ import annotations
"""API router aggregating all endpoints."""
from fastapi import APIRouter

from app.api import intents, timeline, state, undo, onboarding
from app.api.blocks import router as blocks_router
from app.api.self_report import router as self_report_router
from app.api.checkin import router as checkin_router
from app.api.beliefs import router as beliefs_router

router = APIRouter()

router.include_router(intents.router, prefix="/intents", tags=["intents"])
router.include_router(timeline.router, prefix="/timeline", tags=["timeline"])
router.include_router(state.router, prefix="/state", tags=["state"])
router.include_router(undo.router, prefix="/undo", tags=["undo"])
router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
router.include_router(blocks_router, prefix="/blocks", tags=["blocks"])
router.include_router(self_report_router, prefix="/self-report", tags=["self-report"])
router.include_router(checkin_router, prefix="/checkin", tags=["checkin"])
router.include_router(beliefs_router, prefix="/beliefs", tags=["beliefs"])
