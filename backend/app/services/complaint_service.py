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

import uuid
import base64
from app.models.database import (
    IncidentModel, AssessmentModel, ManualOverrideModel, AuditLogModel, ComplaintModel,
    EvidenceModel, StatusHistoryModel
)
from app.models.schemas import (
    CitizenComplaintCreate, CitizenComplaintResponse, RiskAssessmentResponse,
    SafetyOverrideResponse, AdminStatusUpdate, AdminAssignmentUpdate,
    AdminDashboardResponse, AssessmentHistoryItem, PublicComplaintTrackingResponse,
    StatusTimelineItem, EvidenceItemResponse
)
from app.core.lifecycle import ComplaintLifecycleStatus, record_status_history, normalize_status
from app.core.hazard_taxonomy import RAIN_HAZARD_TAXONOMY, classify_hazard_from_text, HazardDefinition
from app.core.gis_service import default_gis_service, ProximityEvaluationResult, WardRoutingResult
from app.core.population_service import default_population_provider, PopulationExposureResult
from app.core.weather_service import default_weather_provider, WeatherData
from app.core.risk_scorer import FactorInputs, compute_risk_score
from app.core.safety_rules import evaluate_safety_rules, SafetyOverrideEvaluation
from app.core.priority_engine import evaluate_sla_status, PriorityQueueItem
from app.services.evidence_service import redact_sensitive_text, EvidenceService
from app.services.gemini_service import gemini_ai_service


class ComplaintService:
    @staticmethod
    def generate_complaint_id() -> str:
        # CIV-2026-XXXXXXXX non-sequential unique alphanumeric ID
        suffix = uuid.uuid4().hex[:8].upper()
        return f"CIV-2026-{suffix}"

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
            category_hint=req.hazard_category_hint or req.category_hint,
            evidence_urls=req.evidence_photos or [],
            consent_given=req.consent_given,
            consent_sms=req.consent_sms,
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

        # Store initial before photos if provided in submission payload
        if req.evidence_photos:
            for idx, photo_item in enumerate(req.evidence_photos):
                try:
                    if photo_item.startswith("data:image"):
                        header, encoded = photo_item.split(",", 1)
                        mime = header.split(";")[0].split(":")[1]
                        raw_bytes = base64.b64decode(encoded)
                    elif len(photo_item) > 100:
                        raw_bytes = base64.b64decode(photo_item)
                        mime = "image/jpeg"
                    else:
                        # Dummy valid JPEG magic bytes for testing
                        raw_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
                        mime = "image/jpeg"
                    EvidenceService.process_and_store_evidence(
                        db=db,
                        complaint_id=complaint_id,
                        file_bytes=raw_bytes,
                        original_filename=f"initial_before_photo_{idx+1}.jpg",
                        declared_mime=mime,
                        evidence_type="before",
                        uploaded_by_role="citizen",
                        uploaded_by_id=req.reporter_name or "citizen_anonymous",
                        caption="Initial before photo submitted by citizen"
                    )
                except Exception:
                    pass

        # Record immutable lifecycle transitions
        record_status_history(
            db=db,
            complaint_id=complaint_id,
            previous_status=None,
            new_status=ComplaintLifecycleStatus.SUBMITTED.value,
            actor_id=req.reporter_name or "citizen_anonymous",
            actor_role="citizen",
            notes="Initial complaint received from citizen portal."
        )
        record_status_history(
            db=db,
            complaint_id=complaint_id,
            previous_status=ComplaintLifecycleStatus.SUBMITTED.value,
            new_status=ComplaintLifecycleStatus.ASSESSED.value,
            actor_id="SYSTEM_RISK_ENGINE",
            actor_role="system",
            notes=f"Automated risk scoring complete: {calculated_score:.1f}/100 ({priority_band})."
        )

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
    def get_public_tracking_dossier(db: Session, complaint_id: str) -> PublicComplaintTrackingResponse:
        """
        Public tracking endpoint:
        Provides complete citizen tracking dossier with status timeline,
        before-and-after proof photos, and resolution summary.
        STRICTLY excludes private reporter details, worker contact numbers, and internal notes.
        """
        incident = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
        if not incident:
            raise KeyError(f"Complaint '{complaint_id}' not found.")

        latest_assessment = (
            db.query(AssessmentModel)
            .filter(AssessmentModel.incident_id == complaint_id)
            .order_by(AssessmentModel.assessed_at.desc())
            .first()
        )
        priority_band = latest_assessment.priority_band if latest_assessment else "Medium"
        haz_def = RAIN_HAZARD_TAXONOMY.get(incident.hazard_type, RAIN_HAZARD_TAXONOMY["other_rain_hazard"])

        # Fetch status timeline
        history_records = (
            db.query(StatusHistoryModel)
            .filter(StatusHistoryModel.complaint_id == complaint_id)
            .order_by(StatusHistoryModel.timestamp.asc())
            .all()
        )
        timeline = [
            StatusTimelineItem(
                timestamp=h.timestamp.isoformat() if h.timestamp else "",
                status=h.new_status,
                actor_role=h.actor_role,
                notes=h.notes if h.actor_role != "administrator" or "internal" not in (h.notes or "").lower() else "Administrative review processed"
            )
            for h in history_records
        ]

        # Fetch evidence photos (Only approved for public viewing)
        evidence_records = (
            db.query(EvidenceModel)
            .filter(EvidenceModel.complaint_id == complaint_id)
            .filter(EvidenceModel.redaction_status == "approved")
            .order_by(EvidenceModel.uploaded_at.asc())
            .all()
        )

        before_photos = [
            EvidenceItemResponse(
                evidence_id=e.evidence_id,
                evidence_type=e.evidence_type,
                original_filename=e.original_filename,
                mime_type=e.mime_type,
                file_size_bytes=e.file_size_bytes,
                uploaded_by_role=e.uploaded_by_role,
                uploaded_by_id=e.uploaded_by_id if e.uploaded_by_role != "citizen" else "citizen",
                uploaded_at=e.uploaded_at.isoformat() if e.uploaded_at else "",
                redaction_status=e.redaction_status,
                view_url=f"/api/evidence/{e.evidence_id}/file",
                caption=e.caption,
                sha256_hash=e.sha256_hash
            )
            for e in evidence_records if e.evidence_type == "before"
        ]

        after_photos = [
            EvidenceItemResponse(
                evidence_id=e.evidence_id,
                evidence_type=e.evidence_type,
                original_filename=e.original_filename,
                mime_type=e.mime_type,
                file_size_bytes=e.file_size_bytes,
                uploaded_by_role=e.uploaded_by_role,
                uploaded_by_id="municipal_field_worker",  # Never expose personal worker id
                uploaded_at=e.uploaded_at.isoformat() if e.uploaded_at else "",
                redaction_status=e.redaction_status,
                view_url=f"/api/evidence/{e.evidence_id}/file",
                caption=e.caption,
                sha256_hash=e.sha256_hash
            )
            for e in evidence_records if e.evidence_type == "after"
        ]

        # Resolution details if completed/verified
        res_desc = None
        action_perf = None
        if incident.resolutions:
            latest_res = incident.resolutions[0]
            if latest_res.verification_status == "verified" or incident.status.upper() == "COMPLETED":
                res_desc = latest_res.description
                action_perf = latest_res.action_taken

        is_reopened = (getattr(incident, "reopened_count", 0) > 0) or (incident.status.upper() == "REOPENED")

        return PublicComplaintTrackingResponse(
            complaint_id=incident.incident_id,
            status=incident.status,
            submitted_at=incident.created_at.isoformat() if incident.created_at else "",
            hazard_category=haz_def.display_name,
            general_description=incident.description or "",
            priority_band=priority_band,
            ward=incident.ward or "Ward 07",
            is_reopened=is_reopened,
            status_timeline=timeline,
            before_photos=before_photos,
            after_photos=after_photos,
            resolution_description=res_desc,
            action_performed=action_perf,
            resolved_at=incident.resolved_at.isoformat() if incident.resolved_at else None,
            tracking_url=f"/api/public/complaints/{incident.incident_id}"
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
