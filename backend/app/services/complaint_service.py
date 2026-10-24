"""
complaint_service.py
Core Complaint Intake, Automatic Assessment, and Triage Engine.
Executes the end-to-end automatic civic assessment pipeline:
Citizen Text -> Hazard NLP Inference -> Location GIS Proximity & Ward Routing ->
Population Exposure Estimation -> Weather Integration -> Time & Recurrence ->
Risk Score Calculation -> Safety Rules Override -> Priority Band Assignment ->
SLA Calculation -> DB Persistence -> Audit Log.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.database import (
    IncidentModel, AssessmentModel, ManualOverrideModel, AuditLogModel, ComplaintModel
)
from app.models.schemas import (
    CitizenComplaintCreate, CitizenComplaintResponse, RiskAssessmentResponse,
    SafetyOverrideResponse, AdminStatusUpdate, AdminAssignmentUpdate,
    AdminDashboardResponse, AssessmentHistoryItem
)
from app.core.hazard_taxonomy import RAIN_HAZARD_TAXONOMY, classify_hazard_from_text, HazardDefinition
from app.core.gis_service import default_gis_service, ProximityEvaluationResult, WardRoutingResult
from app.core.population_service import default_population_provider, PopulationExposureResult
from app.core.weather_service import default_weather_provider, WeatherData
from app.core.risk_scorer import FactorInputs, compute_risk_score
from app.core.safety_rules import evaluate_safety_rules, SafetyOverrideEvaluation
from app.core.priority_engine import evaluate_sla_status, PriorityQueueItem
from app.services.evidence_service import redact_sensitive_text
from app.services.gemini_service import gemini_ai_service


class ComplaintService:
    @staticmethod
    def generate_complaint_id() -> str:
        # e.g. CMP-2026-8A3F
        ts_suffix = hex(int(time.time() * 1000))[-4:].upper()
        return f"CMP-2026-{ts_suffix}"

    @staticmethod
    def submit_citizen_complaint(db: Session, req: CitizenComplaintCreate) -> CitizenComplaintResponse:
        now = datetime.now(timezone.utc)
        complaint_id = ComplaintService.generate_complaint_id()

        # 1. Privacy Protection: Redact phone numbers and plates from description
        sanitized_description, was_redacted = redact_sensitive_text(req.description)

        # 2. Automated Incident Analysis & Hazard Classification (with Spatial GPS context)
        ai_result = gemini_ai_service.analyze_complaint(
            text=req.description,
            location_description=req.location_address,
            user_hint=req.hazard_category_hint,
            latitude=req.latitude,
            longitude=req.longitude,
        )
        if ai_result.detected_hazard_type in RAIN_HAZARD_TAXONOMY:
            hazard_def = RAIN_HAZARD_TAXONOMY[ai_result.detected_hazard_type]
            hazard_severity = ai_result.hazard_severity
            hazard_confidence = ai_result.confidence_score
            hazard_explanation = f"Automated Assessment: {ai_result.ai_reasoning_summary}"
        else:
            hazard_def, hazard_confidence, hazard_explanation = classify_hazard_from_text(
                description=req.description,
                user_category_hint=req.hazard_category_hint
            )
            hazard_severity = hazard_def.severity

        # 3. GIS & Sensitive-Site Proximity (S)
        proximity_eval = default_gis_service.calculate_sensitive_site_proximity(req.latitude, req.longitude)
        norm_s = proximity_eval.normalized_s

        # 4. Ward Routing & Boundary Dispute Detection
        ward_routing = default_gis_service.resolve_ward_and_department(
            lat=req.latitude,
            lon=req.longitude,
            hazard_type=hazard_def.category_id
        )
        assigned_ward = ward_routing.assigned_ward
        assigned_dept = hazard_def.primary_department

        # 5. Population Exposure Estimation (P)
        pop_eval = default_population_provider.estimate_exposure(
            latitude=req.latitude,
            longitude=req.longitude,
            hazard_category=hazard_def.category_id,
            evidence_status="reported"
        )
        norm_p = pop_eval.normalized_p

        # 6. Weather Risk (W)
        weather_eval = default_weather_provider.get_weather_risk(
            latitude=req.latitude,
            longitude=req.longitude,
            ward=assigned_ward
        )
        norm_w = weather_eval.normalized_w

        # 7. Time Outstanding (T) - Just submitted = 0.0
        norm_t = 0.0

        # 8. Recurrence (C) - Historical check in same ward/cluster
        # Distinct past incidents within 30 days (excluding immediate ongoing event < 1 hr to prevent duplicate inflation)
        past_count = (
            db.query(IncidentModel)
            .filter(IncidentModel.ward == assigned_ward)
            .filter(IncidentModel.hazard_type == hazard_def.category_id)
            .filter(IncidentModel.created_at < now - timedelta(hours=1))
            .count()
        )
        norm_c = min(1.0, round(past_count / 5.0, 2))

        # 9. Compute Deterministic Mathematical Risk Score (0 - 100)
        # R = 100 * (0.25H + 0.20S + 0.20P + 0.15W + 0.10T + 0.10C)
        factor_inputs = FactorInputs(
            hazard_severity=hazard_severity,
            sensitive_site_proximity=norm_s,
            population_exposed=norm_p,
            weather_risk=norm_w,
            time_outstanding=norm_t,
            recurrence=norm_c,
        )
        risk_calc = compute_risk_score(factor_inputs)
        calculated_score = risk_calc.rounded_score
        factor_contributions = risk_calc.factor_contributions

        # 10. Independent Safety Override Evaluation
        factors_dict = {
            "hazard_severity": hazard_severity,
            "sensitive_site_proximity": norm_s,
            "population_exposed": norm_p,
            "weather_risk": norm_w,
            "time_outstanding": norm_t,
            "recurrence": norm_c,
        }
        safety_eval = evaluate_safety_rules(
            hazard_type=hazard_def.category_id,
            factors=factors_dict,
            evidence_status="reported"
        )
        if ai_result.emergency_safety_override and not safety_eval.active:
            safety_eval.active = True
            safety_eval.effective_severity = "Critical"
            safety_eval.summary_explanation = f"AI Emergency Safety Override ({ai_result.ai_model_used}): {ai_result.ai_reasoning_summary}"

        # 11. Determine Priority Band & Recommended Action
        if safety_eval.active:
            priority_band = safety_eval.effective_severity or "Critical"
        else:
            if calculated_score >= 80.0:
                priority_band = "Critical"
            elif calculated_score >= 60.0:
                priority_band = "High"
            elif calculated_score >= 35.0:
                priority_band = "Medium"
            else:
                priority_band = "Routine"

        # 12. Calculate SLA Deadline
        if priority_band == "Critical":
            sla_hours = hazard_def.sla_hours_critical
            response_window = f"Immediate Dispatch ({sla_hours:.1f} Hours SLA)"
        elif priority_band == "High":
            sla_hours = hazard_def.sla_hours_high
            response_window = f"Urgent Response ({sla_hours:.1f} Hours SLA)"
        elif priority_band == "Medium":
            sla_hours = 6.0
            response_window = "Standard Service (6 Hours SLA)"
        else:
            sla_hours = hazard_def.sla_hours_routine
            response_window = f"Routine Maintenance ({sla_hours:.0f} Hours SLA)"

        sla_deadline = now + timedelta(hours=sla_hours)

        # 13. Construct Plain-Language Explanation
        explanations: List[str] = []
        if safety_eval.active:
            explanations.append(f"SAFETY OVERRIDE ACTIVATED: {safety_eval.summary_explanation}")
        if ai_result.ai_reasoning_summary:
            explanations.append(f"Assessment: {ai_result.ai_reasoning_summary}")
        explanations.append(f"Classified as '{hazard_def.display_name}' with physical hazard severity {hazard_severity:.2f}.")
        explanations.append(proximity_eval.explanation)
        explanations.append(pop_eval.explanation)
        explanations.append(weather_eval.explanation)
        if ward_routing.is_boundary_dispute:
            explanations.append(ward_routing.explanation)

        plain_language_summary = " • ".join(explanations)

        # 14. Uncertainty Flags
        uncertainty_flags: List[str] = []
        if proximity_eval.proximity_status == "unknown_coordinates":
            uncertainty_flags.append(proximity_eval.explanation)
        if pop_eval.population_exposure_status == "unknown":
            uncertainty_flags.append(pop_eval.explanation)
        if weather_eval.is_missing:
            uncertainty_flags.append(weather_eval.explanation)
        if was_redacted:
            uncertainty_flags.append("Sensitive contact/plate details automatically redacted from public dossier.")

        # 15. Persist Incident / Complaint Model
        incident = IncidentModel(
            incident_id=complaint_id,
            hazard_type=hazard_def.category_id,
            title=f"{hazard_def.display_name} - {assigned_ward}",
            description=sanitized_description,
            ward=assigned_ward,
            latitude=req.latitude,
            longitude=req.longitude,
            created_at=now,
            evidence_status="reported",
            sla_deadline=sla_deadline,
            assigned_department=assigned_dept,
            reporter_name=req.reporter_name,
            reporter_phone=req.reporter_phone,
            reporter_email=req.reporter_email,
            location_address=req.location_address,
            category_hint=req.hazard_category_hint,
            evidence_urls=req.evidence_photos or [],
            consent_given=req.consent_given,
            boundary_dispute=ward_routing.is_boundary_dispute,
            disputed_wards=ward_routing.disputed_wards,
            status="submitted",
            ai_reasoning_summary=ai_result.ai_reasoning_summary,
            ai_model_used=ai_result.ai_model_used,
            ai_analysis_status=ai_result.analysis_status,
            ai_detected_hazard=ai_result.detected_hazard_type,
            ai_confidence_score=ai_result.confidence_score,
        )
        db.add(incident)
        db.commit()

        # 16. Persist Assessment Model
        safety_json = {
            "active": safety_eval.active,
            "effective_severity": safety_eval.effective_severity,
            "triggered_rules": [r.model_dump(mode="json") for r in safety_eval.triggered_rules],
            "manual_override": safety_eval.manual_override,
            "summary": safety_eval.summary_explanation,
        }

        assessment = AssessmentModel(
            incident_id=complaint_id,
            assessed_at=now,
            risk_score=calculated_score,
            priority_band=priority_band,
            formula_version="v1.0.0",
            factor_values=factors_dict,
            factor_contributions=factor_contributions,
            factor_sources={
                "hazard_severity": "24_category_rain_hazard_taxonomy",
                "sensitive_site_proximity": proximity_eval.proximity_status,
                "population_exposed": pop_eval.data_source,
                "weather_risk": weather_eval.weather_status,
                "time_outstanding": "timestamp_elapsed_function",
                "recurrence": "historical_ward_incident_index",
            },
            uncertainty_flags=uncertainty_flags,
            safety_override=safety_json,
            sla_status="within_sla",
            recommended_action=hazard_def.recommended_action,
            explanations=explanations,
        )
        db.add(assessment)
        db.commit()

        # 17. Tamper-Evident Audit Log
        audit = AuditLogModel(
            incident_id=complaint_id,
            action_type="COMPLAINT_SUBMITTED",
            details={
                "hazard_category": hazard_def.category_id,
                "risk_score": calculated_score,
                "priority_band": priority_band,
                "safety_override": safety_eval.active,
                "boundary_dispute": ward_routing.is_boundary_dispute,
            },
            actor="CITIZEN_PUBLIC_PORTAL",
            timestamp=now,
        )
        db.add(audit)
        db.commit()

        return CitizenComplaintResponse(
            complaint_id=complaint_id,
            status="submitted",
            hazard_category=hazard_def.category_id,
            hazard_display_name=hazard_def.display_name,
            risk_score=calculated_score,
            priority_band=priority_band,
            assigned_department=assigned_dept,
            assigned_ward=assigned_ward,
            is_boundary_dispute=ward_routing.is_boundary_dispute,
            disputed_wards=ward_routing.disputed_wards,
            sla_deadline=sla_deadline,
            estimated_response_window=response_window,
            plain_language_explanation=plain_language_summary,
            recommended_action=hazard_def.recommended_action,
            safety_override_active=safety_eval.active,
            evidence_status="reported",
            tracking_url=f"/api/complaints/{complaint_id}",
            submitted_at=now,
            ai_reasoning_summary=ai_result.ai_reasoning_summary,
            ai_model_used=ai_result.ai_model_used,
            ai_analysis_status=ai_result.analysis_status,
            ai_confidence_score=ai_result.confidence_score,
        )

    @staticmethod
    def get_public_complaint(db: Session, complaint_id: str) -> CitizenComplaintResponse:
        incident = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
        if not incident:
            raise KeyError(f"Complaint '{complaint_id}' not found.")

        latest_assessment = (
            db.query(AssessmentModel)
            .filter(AssessmentModel.incident_id == complaint_id)
            .order_by(AssessmentModel.assessed_at.desc())
            .first()
        )

        haz_def = RAIN_HAZARD_TAXONOMY.get(incident.hazard_type, RAIN_HAZARD_TAXONOMY["other_rain_hazard"])
        risk_score = latest_assessment.risk_score if latest_assessment else 50.0
        priority_band = latest_assessment.priority_band if latest_assessment else "Medium"
        safety_active = latest_assessment.safety_override.get("active", False) if latest_assessment else False
        plain_exp = " • ".join(latest_assessment.explanations) if latest_assessment else "Complaint intake recorded."
        rec_action = latest_assessment.recommended_action if latest_assessment else haz_def.recommended_action

        return CitizenComplaintResponse(
            complaint_id=incident.incident_id,
            status=incident.status,
            hazard_category=incident.hazard_type,
            hazard_display_name=haz_def.display_name,
            risk_score=risk_score,
            priority_band=priority_band,
            assigned_department=incident.assigned_department,
            assigned_ward=incident.ward,
            is_boundary_dispute=incident.boundary_dispute,
            disputed_wards=incident.disputed_wards or [],
            sla_deadline=incident.sla_deadline,
            estimated_response_window="In Progress",
            plain_language_explanation=plain_exp,
            recommended_action=rec_action,
            safety_override_active=safety_active,
            evidence_status=incident.evidence_status,
            tracking_url=f"/api/complaints/{incident.incident_id}",
            submitted_at=incident.created_at,
            ai_reasoning_summary=incident.ai_reasoning_summary,
            ai_model_used=incident.ai_model_used,
            ai_analysis_status=incident.ai_analysis_status,
            ai_confidence_score=incident.ai_confidence_score,
        )

    @staticmethod
    def list_complaints(
        db: Session,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[CitizenComplaintResponse]:
        query = db.query(IncidentModel).order_by(IncidentModel.created_at.desc())
        if status_filter:
            query = query.filter(IncidentModel.status == status_filter)
        incidents = query.offset(offset).limit(limit).all()

        results = []
        for inc in incidents:
            results.append(ComplaintService.get_public_complaint(db, inc.incident_id))
        return results

    @staticmethod
    def update_complaint_status(
        db: Session,
        complaint_id: str,
        req: AdminStatusUpdate
    ) -> CitizenComplaintResponse:
        incident = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
        if not incident:
            raise KeyError(f"Complaint '{complaint_id}' not found.")

        old_status = incident.status
        incident.status = req.status
        if req.status == "verified":
            incident.evidence_status = "officially_verified"
        elif req.status == "resolved":
            incident.resolved_at = datetime.now(timezone.utc)
            if req.notes:
                incident.resolution_notes = req.notes

        db.commit()

        # Audit log
        audit = AuditLogModel(
            incident_id=complaint_id,
            action_type="STATUS_UPDATED",
            details={"old_status": old_status, "new_status": req.status, "notes": req.notes},
            actor=req.officer_name,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(audit)
        db.commit()

        return ComplaintService.get_public_complaint(db, complaint_id)

    @staticmethod
    def update_complaint_assignment(
        db: Session,
        complaint_id: str,
        req: AdminAssignmentUpdate
    ) -> CitizenComplaintResponse:
        incident = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
        if not incident:
            raise KeyError(f"Complaint '{complaint_id}' not found.")

        old_dept = incident.assigned_department
        incident.assigned_department = req.assigned_department
        if req.assigned_ward:
            incident.ward = req.assigned_ward
            # Clear boundary dispute once authorized reassignment occurs
            incident.boundary_dispute = False

        db.commit()

        # Audit log
        audit = AuditLogModel(
            incident_id=complaint_id,
            action_type="DEPARTMENT_REASSIGNED",
            details={
                "old_department": old_dept,
                "new_department": req.assigned_department,
                "ward": incident.ward,
                "reason": req.reason,
            },
            actor=req.authorized_by,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(audit)
        db.commit()

        return ComplaintService.get_public_complaint(db, complaint_id)

    @staticmethod
    def get_admin_dashboard(db: Session) -> AdminDashboardResponse:
        now = datetime.now(timezone.utc)
        all_incidents = db.query(IncidentModel).all()
        total_complaints = len(all_incidents)

        critical_count = 0
        high_count = 0
        medium_count = 0
        routine_count = 0
        safety_overrides_count = 0
        sla_breaches_count = 0
        boundary_disputes_count = 0
        awaiting_verification_count = 0

        for inc in all_incidents:
            if inc.evidence_status == "reported":
                awaiting_verification_count += 1
            if inc.boundary_dispute:
                boundary_disputes_count += 1

            # Check latest assessment
            latest = (
                db.query(AssessmentModel)
                .filter(AssessmentModel.incident_id == inc.incident_id)
                .order_by(AssessmentModel.assessed_at.desc())
                .first()
            )
            if latest:
                band = latest.priority_band
                if band == "Critical":
                    critical_count += 1
                elif band == "High":
                    high_count += 1
                elif band == "Medium":
                    medium_count += 1
                else:
                    routine_count += 1

                if latest.safety_override.get("active", False):
                    safety_overrides_count += 1

            if inc.sla_deadline and now > (inc.sla_deadline.replace(tzinfo=timezone.utc) if inc.sla_deadline.tzinfo is None else inc.sla_deadline):
                sla_breaches_count += 1

        from app.config import active_config
        return AdminDashboardResponse(
            total_complaints=total_complaints,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            routine_count=routine_count,
            awaiting_verification_count=awaiting_verification_count,
            safety_overrides_count=safety_overrides_count,
            sla_breaches_count=sla_breaches_count,
            boundary_disputes_count=boundary_disputes_count,
            active_weights=active_config.weights.model_dump(),
            formula_version=active_config.version,
            server_timestamp=now,
        )
