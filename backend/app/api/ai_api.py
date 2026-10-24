"""
ai_api.py
FastAPI router for Google Gemini AI automated civic hazard analysis,
triage recommendations, and real-time model status.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from app.config import active_config
from app.models.schemas import AIAnalysisRequest, AIAnalysisResponse
from app.services.gemini_service import gemini_ai_service

router = APIRouter(prefix="/api/ai", tags=["AI Triage & Synthesis"])


@router.get("/status")
def get_ai_status():
    """Returns the operational status and active configuration of the Gemini AI engine."""
    has_key = bool(active_config.gemini.api_key)
    return {
        "status": "ready" if has_key else "unconfigured_key",
        "service": "Google Gemini Civic Hazard Triage",
        "primary_model": active_config.gemini.model_name,
        "fallback_models": active_config.gemini.fallback_models,
        "api_key_configured": has_key,
        "ai_enabled": active_config.gemini.enabled,
        "timeout_seconds": active_config.gemini.timeout_seconds,
        "server_timestamp": datetime.now(timezone.utc),
    }


@router.post("/analyze", response_model=AIAnalysisResponse)
def analyze_civic_text(req: AIAnalysisRequest):
    """
    Submits civic complaint text for real-time automated Gemini AI analysis,
    extracting hazard classification, severity, life-safety override cues,
    sensitive facility proximity, and transparent AI reasoning.
    """
    try:
        result = gemini_ai_service.analyze_complaint(
            text=req.description,
            location_description=req.location,
            user_hint=req.category_hint,
        )
        return AIAnalysisResponse(
            detected_hazard_type=result.detected_hazard_type,
            hazard_title=result.hazard_title,
            hazard_severity=result.hazard_severity,
            emergency_safety_override=result.emergency_safety_override,
            emergency_rule_candidate=result.emergency_rule_candidate,
            sensitive_site_cues=result.sensitive_site_cues,
            population_exposure_cues=result.population_exposure_cues,
            recommended_department=result.recommended_department,
            recommended_urgency=result.recommended_urgency,
            ai_reasoning_summary=result.ai_reasoning_summary,
            ai_model_used=result.ai_model_used,
            analysis_status=result.analysis_status,
            confidence_score=result.confidence_score,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")
