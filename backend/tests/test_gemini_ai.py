"""
test_gemini_ai.py
Automated tests for Google Gemini AI Civic Hazard Triage and Analysis integration.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import active_config
from app.services.gemini_service import gemini_ai_service, GeminiCivicAIService

client = TestClient(app)


def test_01_gemini_status_endpoint():
    """Verify /api/ai/status returns operational model info and configured state."""
    res = client.get("/api/ai/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["ready", "unconfigured_key"]
    assert data["primary_model"] == "gemini-3.5-flash-lite"
    assert data["api_key_configured"] is True
    assert "gemini-3.1-flash-lite" in data["fallback_models"]


def test_02_direct_gemini_analysis_endpoint():
    """Verify POST /api/ai/analyze extracts hazard classification, cues, and reasoning."""
    payload = {
        "description": "Water is accumulating near a school, and an uncovered manhole is visible during heavy rain.",
        "location": "Near Ward 07 Primary School",
        "category_hint": "open_manhole"
    }
    res = client.post("/api/ai/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["detected_hazard_type"] in ["open_manhole", "waterlog_sensitive_site"]
    assert data["hazard_severity"] >= 0.80
    assert data["emergency_safety_override"] is True
    assert len(data["ai_reasoning_summary"]) > 20
    assert data["analysis_status"] in ["gemini_analyzed", "automated_analyzed", "fallback_heuristic"]


def test_03_citizen_intake_populates_ai_fields():
    """Verify submitting a citizen complaint automatically triggers Gemini and saves AI reasoning."""
    payload = {
        "description": "Live electrical transformer wire has fallen into flooded knee-deep rainwater right outside a hospital entrance.",
        "latitude": 16.5050,
        "longitude": 80.6470,
        "location_address": "City General Hospital Gate 2",
        "reporter_name": "Dr. Ramesh Patel",
        "reporter_phone": "+91-9876543210"
    }
    res = client.post("/api/complaints/submit", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["complaint_id"].startswith(("CMP-2026-", "CIV-2026-"))
    assert data["priority_band"] == "Critical"
    assert data["safety_override_active"] is True
    assert data["ai_reasoning_summary"] is not None
    assert len(data["ai_reasoning_summary"]) > 10
    assert data["ai_model_used"] is not None
    assert data["ai_analysis_status"] in ["gemini_analyzed", "automated_analyzed", "fallback_heuristic"]

    # Verify public tracking endpoint does not leak reporter details but keeps AI summary
    track_res = client.get(f"/api/complaints/{data['complaint_id']}")
    assert track_res.status_code == 200
    track_data = track_res.json()
    assert "Dr. Ramesh Patel" not in str(track_data)
    assert "+91-9876543210" not in str(track_data)
    assert track_data["ai_reasoning_summary"] == data["ai_reasoning_summary"]


def test_04_gemini_heuristic_fallback_when_disabled():
    """Verify graceful zero-downtime heuristic fallback when AI is temporarily disabled."""
    service = GeminiCivicAIService()
    original_enabled = service.config.enabled
    try:
        service.config.enabled = False
        fallback_res = service.analyze_complaint(
            text="Uncovered manhole next to elementary school during rainstorm.",
            location_description="St. Mary School",
            user_hint="open_manhole"
        )
        assert fallback_res.analysis_status == "fallback_heuristic"
        assert fallback_res.detected_hazard_type == "open_manhole"
        assert fallback_res.emergency_safety_override is True
        assert "school" in fallback_res.sensitive_site_cues
        assert "Heuristic NLP analysis" in fallback_res.ai_reasoning_summary
    finally:
        service.config.enabled = original_enabled
