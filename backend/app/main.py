"""
main.py
FastAPI application entrypoint for the Civic Risk Scoring & Priority Engine.
Provides REST endpoints, Swagger UI documentation, CORS, and database initialization.
"""

import os
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.models.database import init_db
from app.api.incidents import router as incidents_router
from app.api.priority import router as priority_router
from app.api.config_api import router as config_router
from app.api.simulation import router as simulation_router
from app.api.complaints import router as complaints_router
from app.api.admin_api import router as admin_router
from app.api.ai_api import router as ai_router
from app.api.worker_api import router as worker_router
from app.api.evidence_api import router as evidence_router
from app.api.public_api import router as public_router

app = FastAPI(
    title="IMPACTX 2026: Explainable Civic Risk Scoring & Priority Engine",
    description="Team OverClock — Intelligent Municipal Incident Triage for Challenge 10: Your City, Your Services.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration configurable via environment
raw_origins = os.environ.get("CORS_ORIGINS", "*")
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SQLite database schema
init_db()

# Include Routers
app.include_router(complaints_router)
app.include_router(admin_router)
app.include_router(worker_router)
app.include_router(evidence_router)
app.include_router(public_router)
app.include_router(ai_router)
app.include_router(incidents_router)
app.include_router(priority_router)
app.include_router(config_router)
app.include_router(simulation_router)


@app.get("/health", tags=["System Health"])
def health_check():
    """
    Health check endpoint returning service status, timestamp, and active formula version.
    """
    from app.config import active_config
    return {
        "status": "healthy",
        "service": "civic-risk-scoring-priority-engine",
        "team": "Team OverClock",
        "competition": "IMPACTX 2026 — Challenge 10",
        "institution": "VIT-AP University",
        "formula_version": active_config.version,
        "active_weights": active_config.weights.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/config/risk", tags=["Model Configuration"])
def get_risk_config_contract():
    """
    Returns active risk scoring formula weights, thresholds, and safety rules
    for team integration contracts.
    """
    from app.config import active_config
    return active_config


# If frontend dist exists, mount as static files for single-command full-stack hosting
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
