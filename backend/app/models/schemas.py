"""
schemas.py
Pydantic schemas for API requests, risk assessments, manual overrides,
priority queues, and configuration endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class FactorInputsSchema(BaseModel):
    hazard_severity: float = Field(..., ge=0.0, le=1.0)
    sensitive_site_proximity: float = Field(..., ge=0.0, le=1.0)
    population_exposed: float = Field(..., ge=0.0, le=1.0)
    weather_risk: float = Field(..., ge=0.0, le=1.0)
    time_outstanding: float = Field(..., ge=0.0, le=1.0)
    recurrence: float = Field(..., ge=0.0, le=1.0)


class CreateIncidentRequest(BaseModel):
    incident_id: str = Field(..., min_length=1, max_length=64, description="Unique incident identifier (e.g. INC-001)")
    hazard_type: str = Field(..., description="Hazard category (e.g. open_manhole, severe_flooding, pothole)")
    title: Optional[str] = None
    description: Optional[str] = None
    ward: Optional[str] = "Ward 07"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: Optional[datetime] = None
    factors: Optional[FactorInputsSchema] = None
    evidence_status: str = Field("reported", description="reported, corroborated, officially_verified")
    sla_deadline: Optional[datetime] = None
    assigned_department: Optional[str] = "Unassigned"


class AssessIncidentRequest(BaseModel):
    factors: Optional[FactorInputsSchema] = None
    hazard_type: Optional[str] = None
    evidence_status: Optional[str] = None
    sla_deadline: Optional[datetime] = None


class SafetyOverrideResponse(BaseModel):
    active: bool = False
    effective_severity: Optional[str] = None
    triggered_rules: List[Dict[str, Any]] = Field(default_factory=list)
    manual_override: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None


class RiskAssessmentResponse(BaseModel):
    incident_id: str
    risk_score: float
    priority_band: str
    safety_override: SafetyOverrideResponse
    factor_contributions: Dict[str, float]
    uncertainty_flags: List[str] = Field(default_factory=list)
    sla_status: str
    sla_deadline: Optional[datetime] = None
    is_sla_breached: bool = False
    explanation: List[str]
    recommended_action: str
    formula_version: str = "v1.0.0"
    assessed_at: datetime
    assigned_department: Optional[str] = "Unassigned"


class ManualOverrideRequest(BaseModel):
    authorized_by: str = Field(..., min_length=1, description="Name or ID of authorizing official")
    role: str = Field("supervisor", description="Role: supervisor, duty_officer, admin")
    reason: str = Field(..., min_length=5, description="Documented justification for manual priority override")
    target_severity: str = Field("Critical", description="Target severity: Critical, High, Medium, Routine")


class AssessmentHistoryItem(BaseModel):
    assessment_id: int
    assessed_at: datetime
    risk_score: float
    priority_band: str
    formula_version: str
    factor_values: Dict[str, float]
    factor_contributions: Dict[str, float]
    safety_override: Dict[str, Any]
    sla_status: str
    recommended_action: str
    explanations: List[str]


class IncidentDetailResponse(BaseModel):
    incident_id: str
    hazard_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    ward: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    evidence_status: str
    sla_deadline: Optional[datetime] = None
    assigned_department: str
    latest_assessment: Optional[RiskAssessmentResponse] = None
    assessment_history: List[AssessmentHistoryItem] = Field(default_factory=list)
    manual_override: Optional[Dict[str, Any]] = None
    audit_logs: List[Dict[str, Any]] = Field(default_factory=list)
    ai_reasoning_summary: Optional[str] = None
    ai_model_used: Optional[str] = None
    ai_analysis_status: Optional[str] = None


class UpdateRiskModelConfigRequest(BaseModel):
    authorized_by: str
    role: str
    weights: Optional[Dict[str, float]] = None
    priority_bands: Optional[Dict[str, float]] = None
    time_escalation_cap_hours: Optional[float] = None


# ==========================================
# CITIZEN INTAKE & ADMIN DASHBOARD SCHEMAS
# ==========================================

class CitizenComplaintCreate(BaseModel):
    description: str = Field(..., min_length=5, description="Citizen's description of civic hazard in plain language")
    latitude: Optional[float] = Field(None, description="GPS latitude from browser geolocation (optional)")
    longitude: Optional[float] = Field(None, description="GPS longitude from browser geolocation (optional)")
    location_address: Optional[str] = Field(None, description="Street address or manual map pin description")
    hazard_category_hint: Optional[str] = Field(None, description="Optional user category suggestion (treated as a hint)")
    evidence_photos: Optional[List[str]] = Field(default_factory=list, description="Base64 or URL references to photos")
    reporter_name: Optional[str] = Field(None, description="Optional contact name (Private, never exposed publicly)")
    reporter_phone: Optional[str] = Field(None, description="Optional contact phone (Private, never exposed publicly)")
    reporter_email: Optional[str] = Field(None, description="Optional contact email (Private, never exposed publicly)")
    consent_given: bool = Field(True, description="Explicit consent for municipal processing")

    @field_validator("latitude")
    @classmethod
    def validate_lat(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-90.0 <= v <= 90.0):
            raise ValueError(f"Latitude {v} out of valid range [-90, +90]")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_lon(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-180.0 <= v <= 180.0):
            raise ValueError(f"Longitude {v} out of valid range [-180, +180]")
        return v


class CitizenComplaintResponse(BaseModel):
    complaint_id: str
    status: str
    hazard_category: str
    hazard_display_name: str
    risk_score: float
    priority_band: str
    assigned_department: str
    assigned_ward: str
    is_boundary_dispute: bool = False
    disputed_wards: List[str] = Field(default_factory=list)
    sla_deadline: Optional[datetime] = None
    estimated_response_window: str
    plain_language_explanation: str
    recommended_action: str
    safety_override_active: bool
    evidence_status: str
    tracking_url: str
    submitted_at: datetime
    # Gemini AI Triage & Synthesis
    ai_reasoning_summary: Optional[str] = None
    ai_model_used: Optional[str] = None
    ai_analysis_status: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    # Notice: Zero private reporter contact details exposed in public response!


class AdminStatusUpdate(BaseModel):
    status: str = Field(..., description="verified, assigned, in_progress, resolved, rejected")
    officer_name: str = Field(..., min_length=2)
    notes: Optional[str] = None


class AdminAssignmentUpdate(BaseModel):
    assigned_department: str = Field(..., min_length=2)
    assigned_ward: Optional[str] = None
    authorized_by: str = Field(..., min_length=2)
    reason: str = Field(..., min_length=4)


class AdminDashboardResponse(BaseModel):
    total_complaints: int
    critical_count: int
    high_count: int
    medium_count: int
    routine_count: int
    awaiting_verification_count: int
    safety_overrides_count: int
    sla_breaches_count: int
    boundary_disputes_count: int
    active_weights: Dict[str, float]
    formula_version: str
    server_timestamp: datetime


class AIAnalysisRequest(BaseModel):
    description: str = Field(..., min_length=3, description="Incident or complaint text to analyze with Gemini")
    location: Optional[str] = Field(None, description="Location description or coordinates")
    category_hint: Optional[str] = Field(None, description="Optional user advisory hint")


class AIAnalysisResponse(BaseModel):
    detected_hazard_type: str
    hazard_title: str
    hazard_severity: float
    emergency_safety_override: bool
    emergency_rule_candidate: Optional[str] = None
    sensitive_site_cues: List[str] = Field(default_factory=list)
    population_exposure_cues: str
    recommended_department: str
    recommended_urgency: str
    ai_reasoning_summary: str
    ai_model_used: str
    analysis_status: str
    confidence_score: float
