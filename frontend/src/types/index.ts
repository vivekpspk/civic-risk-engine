/**
 * TypeScript interfaces matching the backend Pydantic models.
 */

export interface FactorInputs {
  hazard_severity: number;
  sensitive_site_proximity: number;
  population_exposed: number;
  weather_risk: number;
  time_outstanding: number;
  recurrence: number;
}

export interface TriggeredSafetyRule {
  rule_id: string;
  rule_name: string;
  condition_matched: string;
  severity_level: string;
  trigger_result: string;
  explanation: string;
  evidence_status: string;
  timestamp: string;
  rule_version: string;
}

export interface SafetyOverride {
  active: boolean;
  effective_severity?: string;
  triggered_rules: TriggeredSafetyRule[];
  manual_override?: {
    authorized_by: string;
    role: string;
    reason: string;
    target_severity: string;
    timestamp?: string;
  };
  summary?: string;
}

export interface RiskAssessmentResponse {
  incident_id: string;
  risk_score: number;
  priority_band: 'Critical' | 'High' | 'Medium' | 'Routine';
  safety_override: SafetyOverride;
  factor_contributions: {
    hazard_severity: number;
    sensitive_site_proximity: number;
    population_exposed: number;
    weather_risk: number;
    time_outstanding: number;
    recurrence: number;
  };
  uncertainty_flags: string[];
  sla_status: 'within_sla' | 'imminent_breach' | 'breached' | 'untracked';
  sla_deadline?: string;
  is_sla_breached: boolean;
  explanation: string[];
  recommended_action: string;
  formula_version: string;
  assessed_at: string;
  assigned_department?: string;
}

export interface PriorityQueueItem {
  queue_rank: number;
  incident_id: string;
  hazard_type: string;
  risk_score: number;
  effective_priority_band: string;
  safety_override_active: boolean;
  safety_override_reason?: string;
  sla_status: string;
  sla_deadline?: string;
  is_sla_breached: boolean;
  evidence_status: string;
  assigned_department: string;
  created_at: string;
  elapsed_minutes: number;
  factor_contributions: Record<string, number>;
  uncertainty_warnings: string[];
  ranking_explanation: string;
  recommended_action: string;
}

export interface AssessmentHistoryItem {
  assessment_id: number;
  assessed_at: string;
  risk_score: number;
  priority_band: string;
  formula_version: string;
  factor_values: Record<string, number>;
  factor_contributions: Record<string, number>;
  safety_override: SafetyOverride;
  sla_status: string;
  recommended_action: string;
  explanations: string[];
}

export interface IncidentDetailResponse {
  incident_id: string;
  hazard_type: string;
  title?: string;
  description?: string;
  ward: string;
  latitude?: number;
  longitude?: number;
  created_at: string;
  evidence_status: string;
  sla_deadline?: string;
  assigned_department: string;
  latest_assessment?: RiskAssessmentResponse;
  assessment_history: AssessmentHistoryItem[];
  manual_override?: {
    authorized_by: string;
    role: string;
    reason: string;
    target_severity: string;
    created_at: string;
  };
  audit_logs: Array<{
    id: number;
    action_type: string;
    details: any;
    actor: string;
    timestamp: string;
  }>;
}

export interface SimulationResult {
  status: string;
  scenario_name: string;
  total_reports_ingested: number;
  report_allocations: {
    school_manhole_reports: number;
    boundary_waterlogging_reports: number;
    coordinated_bot_attack_reports: number;
    genuine_emergency_in_attack_zone: number;
    routine_civic_issues_reports: number;
    total_verified: number;
  };
  proposed_clusters_count: number;
  incidents_triaged_count: number;
  safety_overrides_triggered: number;
  sla_breaches_detected: number;
  missing_data_warnings_count: number;
  genuine_hazard_preserved_under_attack: boolean;
  highest_priority_incidents: Array<{
    queue_rank: number;
    incident_id: string;
    hazard_type: string;
    risk_score: number;
    effective_priority_band: string;
    safety_override_active: boolean;
    sla_status: string;
    recommended_action: string;
  }>;
  department_assignments: Record<string, number>;
  timestamp: string;
}

export interface RiskModelConfig {
  version: string;
  formula: string;
  status: string;
  label: string;
  weights: {
    hazard_severity: number;
    sensitive_site_proximity: number;
    population_exposed: number;
    weather_risk: number;
    time_outstanding: number;
    recurrence: number;
  };
  priority_bands: {
    critical_min: number;
    high_min: number;
    medium_min: number;
    routine_min: number;
  };
  hazard_severity_map: Record<string, number>;
  safety_rules: Array<{
    rule_id: string;
    name: string;
    condition_description: string;
    hazard_types: string[];
    min_proximity?: number;
    min_weather_risk?: number;
    min_population?: number;
    severity_level: string;
    explanation: string;
  }>;
  time_escalation_cap_hours: number;
}

export interface CitizenComplaintCreate {
  description: string;
  latitude?: number | null;
  longitude?: number | null;
  location_address?: string;
  hazard_category_hint?: string;
  evidence_photos?: string[];
  reporter_name?: string;
  reporter_phone?: string;
  reporter_email?: string;
  consent_given?: boolean;
}

export interface CitizenComplaintResponse {
  complaint_id: string;
  status: string;
  hazard_category: string;
  hazard_display_name: string;
  risk_score: number;
  priority_band: 'Critical' | 'High' | 'Medium' | 'Routine';
  assigned_department: string;
  assigned_ward: string;
  is_boundary_dispute: boolean;
  disputed_wards: string[];
  sla_deadline?: string;
  estimated_response_window: string;
  plain_language_explanation: string;
  recommended_action: string;
  safety_override_active: boolean;
  evidence_status: string;
  tracking_url: string;
  submitted_at: string;
  ai_reasoning_summary?: string;
  ai_model_used?: string;
  ai_analysis_status?: string;
  ai_confidence_score?: number;
}

export interface AdminDashboardData {
  total_complaints: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  routine_count: number;
  awaiting_verification_count: number;
  safety_overrides_count: number;
  sla_breaches_count: number;
  boundary_disputes_count: number;
  active_weights: Record<string, number>;
  formula_version: string;
  server_timestamp: string;
}

export interface AIAnalysisRequest {
  description: string;
  location?: string;
  category_hint?: string;
}

export interface AIAnalysisResponse {
  detected_hazard_type: string;
  hazard_title: string;
  hazard_severity: number;
  emergency_safety_override: boolean;
  emergency_rule_candidate?: string;
  sensitive_site_cues: string[];
  population_exposure_cues: string;
  recommended_department: string;
  recommended_urgency: string;
  ai_reasoning_summary: string;
  ai_model_used: string;
  analysis_status: string;
  confidence_score: number;
}

export interface AIStatusResponse {
  status: string;
  service: string;
  primary_model: string;
  fallback_models: string[];
  api_key_configured: boolean;
  ai_enabled: boolean;
  timeout_seconds: number;
  server_timestamp: string;
}
