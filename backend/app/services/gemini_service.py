"""
gemini_service.py
Google Gemini AI service for automated natural language civic complaint analysis,
hazard classification, emergency cue detection, and explainable AI synthesis.
"""

import json
import logging
from typing import Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from app.config import active_config
from app.core.hazard_taxonomy import (
    RAIN_HAZARD_TAXONOMY,
    HazardDefinition,
    classify_hazard_from_text,
)

logger = logging.getLogger(__name__)


class GeminiAnalysisResult(BaseModel):
    detected_hazard_type: str = Field(description="Taxonomy key for the detected hazard")
    hazard_title: str = Field(description="Human-readable title of hazard")
    hazard_severity: float = Field(ge=0.0, le=1.0, description="Normalized severity score")
    emergency_safety_override: bool = Field(False, description="Whether immediate safety override is warranted")
    emergency_rule_candidate: Optional[str] = Field(None, description="Suggested rule ID, e.g. RULE-001")
    sensitive_site_cues: List[str] = Field(default_factory=list, description="Extracted sensitive proximity cues")
    population_exposure_cues: str = Field("medium", description="Estimated population risk band")
    recommended_department: str = Field(description="Responsible civic department")
    recommended_urgency: str = Field("Medium", description="Triage urgency band")
    ai_reasoning_summary: str = Field(description="Transparent, human-readable AI explanation of the situation")
    ai_model_used: str = Field(description="Gemini model that performed the analysis")
    analysis_status: str = Field("gemini_analyzed", description="Status: gemini_analyzed or fallback_heuristic")
    confidence_score: float = Field(0.85, ge=0.0, le=1.0)


TAXONOMY_KEYS = list(RAIN_HAZARD_TAXONOMY.keys())


class GeminiCivicAIService:
    def __init__(self):
        self.config = active_config.gemini

    def _call_gemini_api(self, prompt: str, model_name: str) -> Optional[dict]:
        """Calls Google Generative Language API for structured JSON response."""
        if not self.config.api_key:
            return None

        url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent"
        headers = {
            "x-goog-api-key": self.config.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0,
            },
        }

        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        return json.loads(raw_text)
                else:
                    logger.warning(
                        f"Gemini API returned status {res.status_code} for model {model_name}: {res.text[:200]}"
                    )
        except Exception as e:
            logger.warning(f"Error invoking Gemini API with {model_name}: {e}")

        return None

    def analyze_complaint(
        self,
        text: str,
        location_description: Optional[str] = None,
        user_hint: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> GeminiAnalysisResult:
        """
        Performs automated triage on citizen complaints.
        Uses intelligent multi-model failover, incorporates spatial GPS coordinates,
        and falls back to deterministic heuristics if unreachable.
        """
        # 1. Deterministic heuristic baseline as safety net
        heuristic_hazard, heuristic_conf, heuristic_expl = classify_hazard_from_text(text, user_hint)

        # If disabled or no API key, return the heuristic baseline immediately
        if not self.config.enabled or not self.config.api_key:
            return self._build_heuristic_result(
                heuristic_hazard, heuristic_conf, heuristic_expl, text, location_description, user_hint
            )

        # 2. Construct prompt incorporating text, location, and GPS coordinates
        allowed_keys_str = ", ".join(TAXONOMY_KEYS)
        gps_str = f"Lat {latitude:.5f}, Lon {longitude:.5f}" if (latitude is not None and longitude is not None) else "Not provided (Using ward center approximation)"
        prompt = f"""You are the automated municipal incident triage engine for municipal emergency operations.
Analyze this citizen-submitted civic report regarding heavy rain, waterlogging, or urban hazards.

Citizen Complaint: "{text}"
Location Address/Description: "{location_description or 'Not specified'}"
Verified GPS Coordinates: "{gps_str}"
User Category Hint: "{user_hint or 'None'}"

Select the most appropriate hazard category from this strict taxonomy:
[{allowed_keys_str}]

Respond ONLY with valid JSON conforming to this schema:
{{
  "detected_hazard_type": "<one of the taxonomy keys above>",
  "hazard_severity_score": <float between 0.0 and 1.0>,
  "emergency_safety_override": <true if direct life-threat, e.g. open manhole near children, live electrical wires in water, trapped people, or structural collapse; else false>,
  "emergency_rule_candidate": "<RULE-001, RULE-002, RULE-005, RULE-006, or null>",
  "sensitive_site_cues": ["<list of sensitive facilities mentioned or nearby: school, kindergarten, hospital, elderly care, transit_hub, fire_station>"],
  "estimated_population_impact": "<low, medium, high, or critical>",
  "recommended_department": "<Drainage & Sewerage, Roads & Traffic Infrastructure, Electrical & Lighting, Disaster Management & Emergency Relief, Health & Sanitation, or Water Supply>",
  "recommended_urgency": "<Routine, Medium, High, or Critical>",
  "confidence_score": <float between 0.50 and 1.0>,
  "ai_reasoning_summary": "<2-3 sentence authoritative municipal safety assessment: identify hazard at this location, immediate physical risks, and ordered field response. Do not mention any AI company names or model versions.>"
}}"""

        # 3. Multi-model execution with fallback
        models_to_try = [self.config.model_name] + [
            m for m in self.config.fallback_models if m != self.config.model_name
        ]

        for model in models_to_try:
            parsed = self._call_gemini_api(prompt, model)
            if parsed and isinstance(parsed, dict) and "detected_hazard_type" in parsed:
                detected_type = parsed.get("detected_hazard_type", "").strip()
                # Verify that the detected type is in our taxonomy, or map to fallback
                if detected_type not in RAIN_HAZARD_TAXONOMY:
                    if detected_type == "open_manhole_in_water":
                        detected_type = "open_manhole"
                    else:
                        detected_type = heuristic_hazard.category_id

                detected_def = RAIN_HAZARD_TAXONOMY[detected_type]
                severity = float(parsed.get("hazard_severity_score", detected_def.severity))
                severity = max(0.0, min(1.0, severity))

                override = bool(parsed.get("emergency_safety_override", False))
                # Life safety enforcement: open manhole, live wire, or trapped people always flagged
                if detected_type in [
                    "open_manhole",
                    "fallen_electric_pole_live_wire",
                    "trapped_people_or_vehicles",
                ]:
                    override = True

                cues = parsed.get("sensitive_site_cues", [])
                if not isinstance(cues, list):
                    cues = [str(cues)]

                reasoning = parsed.get(
                    "ai_reasoning_summary",
                    f"Classified as {detected_def.display_name} with severity {severity:.2f}. "
                    f"Assigned to {detected_def.primary_department} with {detected_def.sla_hours_high}h SLA.",
                )

                return GeminiAnalysisResult(
                    detected_hazard_type=detected_type,
                    hazard_title=detected_def.display_name,
                    hazard_severity=severity,
                    emergency_safety_override=override,
                    emergency_rule_candidate=parsed.get("emergency_rule_candidate"),
                    sensitive_site_cues=cues,
                    population_exposure_cues=str(parsed.get("estimated_population_impact", "medium")),
                    recommended_department=parsed.get("recommended_department", detected_def.primary_department),
                    recommended_urgency=parsed.get("recommended_urgency", "High" if override else "Medium"),
                    ai_reasoning_summary=reasoning,
                    ai_model_used="Automated Civic Triage Engine",
                    analysis_status="automated_analyzed",
                    confidence_score=float(parsed.get("confidence_score", 0.92)),
                )

        # 4. Fallback to heuristic if all model calls failed/timed out
        logger.info("External calls did not succeed; falling back to deterministic heuristic classification.")
        return self._build_heuristic_result(
            heuristic_hazard, heuristic_conf, heuristic_expl, text, location_description, user_hint
        )

    def _build_heuristic_result(
        self,
        hazard: HazardDefinition,
        conf: float,
        explanation: str,
        text: str,
        location: Optional[str],
        hint: Optional[str],
    ) -> GeminiAnalysisResult:
        is_override = hazard.urgent_review_required or hazard.category_id in [
            "open_manhole",
            "fallen_electric_pole_live_wire",
            "trapped_people_or_vehicles",
        ]
        sensitive_cues = []
        lower_text = (text + " " + (location or "")).lower()
        for site in ["school", "hospital", "transit", "station", "kindergarten", "elderly"]:
            if site in lower_text:
                sensitive_cues.append(site)

        reasoning = (
            f"Heuristic NLP analysis classified incident as '{hazard.display_name}' (confidence {conf:.2f}). "
            f"Severity set to {hazard.severity:.2f}. Directed to {hazard.primary_department}."
        )
        if is_override:
            reasoning += " Life-safety override candidate triggered due to severe physical hazard profile."

        return GeminiAnalysisResult(
            detected_hazard_type=hazard.category_id,
            hazard_title=hazard.display_name,
            hazard_severity=hazard.severity,
            emergency_safety_override=is_override,
            emergency_rule_candidate="RULE-001" if hazard.category_id == "open_manhole" else None,
            sensitive_site_cues=sensitive_cues,
            population_exposure_cues="high" if len(sensitive_cues) > 0 else "medium",
            recommended_department=hazard.primary_department,
            recommended_urgency="Critical" if is_override else "Medium",
            ai_reasoning_summary=reasoning,
            ai_model_used="deterministic_heuristic_v1",
            analysis_status="fallback_heuristic",
            confidence_score=conf,
        )


# Global singleton instance
gemini_ai_service = GeminiCivicAIService()
