"""AI Timebox Backend - Main FastAPI Application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.api.blocks import router as blocks_router
from app.api.self_report import router as self_report_router
from app.api.checkin import router as checkin_router
from app.api.beliefs import router as beliefs_router
from app.core.config import settings

app = FastAPI(
    title="AI Timebox",
    description="Cognitive Calendar API - Human-state aware time orchestration",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix="/api")
app.include_router(blocks_router)
app.include_router(self_report_router)
app.include_router(checkin_router)
app.include_router(beliefs_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
