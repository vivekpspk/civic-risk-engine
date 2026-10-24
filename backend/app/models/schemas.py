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
    consent_sms: bool = Field(True, description="Consent for receiving SMS updates")
    category_hint: Optional[str] = Field(None, description="Optional user category suggestion")

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


# ==========================================
# WORKER & EVIDENCE LIFECYCLE SCHEMAS
# ==========================================

class EvidenceItemResponse(BaseModel):
    evidence_id: str
    evidence_type: str  # "before" or "after"
    original_filename: str
    mime_type: str
    file_size_bytes: int
    uploaded_by_role: str
    uploaded_by_id: str
    uploaded_at: str
    redaction_status: str
    view_url: str
    caption: Optional[str] = None
    sha256_hash: Optional[str] = None


class EvidenceComparisonResponse(BaseModel):
    complaint_id: str
    title: str
    status: str
    ward: str
    before_evidence: List[EvidenceItemResponse]
    after_evidence: List[EvidenceItemResponse]
    total_before_count: int
    total_after_count: int
    resolution_summary: Optional[Dict[str, Any]] = None


class WorkerSummaryResponse(BaseModel):
    worker_id: str
    name: str
    phone: str
    department: str
    ward: str
    status: str
    active_tasks_count: int


class WorkerTaskResponse(BaseModel):
    task_id: int
    complaint_id: str
    worker_id: str
    status: str  # assigned, accepted, in_progress, completed, unable_to_resolve
    assigned_at: str
    instructions: Optional[str] = None
    target_completion_time: Optional[str] = None
    hazard_title: str
    ward: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_address: Optional[str] = None
    priority_band: str
    risk_score: float
    safety_override_active: bool


class WorkerAcceptRequest(BaseModel):
    worker_id: str = Field(..., min_length=2)
    notes: Optional[str] = None


class WorkerStartRequest(BaseModel):
    worker_id: str = Field(..., min_length=2)
    inspection_notes: Optional[str] = None


class WorkerUnableToResolveRequest(BaseModel):
    worker_id: str = Field(..., min_length=2)
    reason: str = Field(..., min_length=5, description="Specific blocker reason preventing resolution")


class WorkerResolutionSubmitRequest(BaseModel):
    worker_id: str = Field(..., min_length=2)
    description: str = Field(..., min_length=5, description="Detailed description of the repair or work performed")
    action_taken: str = Field(..., min_length=3, description="Specific physical action executed")
    after_evidence_ids: List[str] = Field(..., min_length=1, description="List of uploaded after-photo evidence IDs")
    completion_latitude: Optional[float] = None
    completion_longitude: Optional[float] = None
    blockers: Optional[str] = None


class AdminAssignWorkerRequest(BaseModel):
    worker_id: str = Field(..., min_length=2, description="Target worker ID to assign")
    admin_id: str = Field(..., min_length=2, description="Admin officer authorizing assignment")
    instructions: Optional[str] = Field(None, description="Operational instructions for the worker")
    target_completion_time: Optional[datetime] = Field(None, description="Target SLA resolution time")


class AdminVerifyResolutionRequest(BaseModel):
    decision: str = Field(..., description="'approve' to mark COMPLETED, 'reject' to return to IN_PROGRESS")
    admin_id: str = Field(..., min_length=2, description="Administrator verifying resolution")
    notes: Optional[str] = Field(None, description="Verification notes or rejection explanation")


class AdminReopenRequest(BaseModel):
    admin_id: str = Field(..., min_length=2)
    reason: str = Field(..., min_length=5, description="Mandatory reason for reopening the complaint")


class AdminRejectRequest(BaseModel):
    admin_id: str = Field(..., min_length=2)
    reason: str = Field(..., min_length=5, description="Mandatory reason for rejecting the complaint")


class StatusTimelineItem(BaseModel):
    timestamp: str
    status: str
    actor_role: str
    notes: Optional[str] = None


class PublicComplaintTrackingResponse(BaseModel):
    complaint_id: str
    status: str
    submitted_at: str
    hazard_category: str
    general_description: str
    priority_band: str
    ward: str
    is_reopened: bool
    status_timeline: List[StatusTimelineItem]
    before_photos: List[EvidenceItemResponse]
    after_photos: List[EvidenceItemResponse]
    resolution_description: Optional[str] = None
    action_performed: Optional[str] = None
    resolved_at: Optional[str] = None
    tracking_url: str

