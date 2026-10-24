"""
incident_service.py
Service managing incident lifecycle, factor extraction, risk evaluation,
persistence, manual overrides, and audit trails.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.database import (
    IncidentModel, AssessmentModel, ManualOverrideModel, AuditLogModel
)
from app.models.schemas import (
    CreateIncidentRequest, AssessIncidentRequest, FactorInputsSchema,
    RiskAssessmentResponse, SafetyOverrideResponse, IncidentDetailResponse,
    AssessmentHistoryItem
)
from app.core.risk_scorer import FactorInputs, compute_risk_score
from app.core.feature_extractor import (
    extract_hazard_severity, extract_sensitive_site_proximity,
    extract_population_exposed, extract_weather_risk,
    extract_time_outstanding, extract_recurrence
)
from app.core.safety_rules import evaluate_safety_rules
from app.core.priority_engine import (
    evaluate_sla_status, rank_priority_queue, PriorityQueueItem
)


class IncidentService:
    @staticmethod
    def create_incident(db: Session, req: CreateIncidentRequest) -> IncidentModel:
        # Check if already exists
        existing = db.query(IncidentModel).filter(IncidentModel.incident_id == req.incident_id).first()
        if existing:
            raise ValueError(f"Incident with ID '{req.incident_id}' already exists.")

        created_at = req.created_at or datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        incident = IncidentModel(
            incident_id=req.incident_id,
            hazard_type=req.hazard_type,
            title=req.title or f"{req.hazard_type.replace('_', ' ').title()} - {req.ward}",
            description=req.description,
            ward=req.ward or "Ward 07",
            latitude=req.latitude,
            longitude=req.longitude,
            created_at=created_at,
            evidence_status=req.evidence_status,
            sla_deadline=req.sla_deadline,
            assigned_department=req.assigned_department or "Unassigned",
        )
        db.add(incident)
        db.commit()

        # Audit log
        audit = AuditLogModel(
            incident_id=req.incident_id,
            action_type="INCIDENT_CREATED",
            details={"hazard_type": req.hazard_type, "ward": req.ward, "evidence_status": req.evidence_status},
            actor="SYSTEM",
            timestamp=datetime.now(timezone.utc),
        )
        db.add(audit)
        db.commit()

        # If initial factors were provided, assess immediately
        if req.factors:
            IncidentService.assess_incident(
                db=db,
                incident_id=req.incident_id,
                req=AssessIncidentRequest(factors=req.factors, evidence_status=req.evidence_status, sla_deadline=req.sla_deadline)
            )

        return incident

    @staticmethod
    def assess_incident(
        db: Session,
        incident_id: str,
        req: Optional[AssessIncidentRequest] = None,
        config=None
    ) -> RiskAssessmentResponse:
        incident = db.query(IncidentModel).filter(IncidentModel.incident_id == incident_id).first()
        if not incident:
            raise KeyError(f"Incident with ID '{incident_id}' not found.")

        # Update fields if provided in assess request
        if req:
            if req.hazard_type:
                incident.hazard_type = req.hazard_type
            if req.evidence_status:
                incident.evidence_status = req.evidence_status
            if req.sla_deadline:
                incident.sla_deadline = req.sla_deadline

        # Check for active manual override
        manual_override_row = db.query(ManualOverrideModel).filter(
            ManualOverrideModel.incident_id == incident_id,
            ManualOverrideModel.is_active == True
        ).order_by(ManualOverrideModel.created_at.desc()).first()

        manual_override_dict = None
        if manual_override_row:
            manual_override_dict = {
                "is_active": True,
                "authorized_by": manual_override_row.authorized_by,
                "role": manual_override_row.role,
                "reason": manual_override_row.reason,
                "severity": manual_override_row.target_severity,
            }

        # Resolve factor values & uncertainties
        uncertainty_warnings: List[str] = []
        factor_sources: Dict[str, str] = {}
        factor_dict: Dict[str, float] = {}

        if req and req.factors:
            # Explicit factor inputs supplied directly
            f = req.factors
            factor_dict = {
                "hazard_severity": f.hazard_severity,
                "sensitive_site_proximity": f.sensitive_site_proximity,
                "population_exposed": f.population_exposed,
                "weather_risk": f.weather_risk,
                "time_outstanding": f.time_outstanding,
                "recurrence": f.recurrence,
            }
            factor_sources = {k: "explicit_api_input" for k in factor_dict}
        else:
            # Extract features from incident metadata
            h_det = extract_hazard_severity(incident.hazard_type, config=config)
            s_det = extract_sensitive_site_proximity()
            p_det, p_warn = extract_population_exposed()
            w_det, w_warn = extract_weather_risk()
            t_det = extract_time_outstanding(incident.created_at, config=config)
            c_det, c_warn = extract_recurrence()

            factor_dict = {
                "hazard_severity": h_det.value,
                "sensitive_site_proximity": s_det.value,
                "population_exposed": p_det.value,
                "weather_risk": w_det.value,
                "time_outstanding": t_det.value,
                "recurrence": c_det.value,
            }
            factor_sources = {
                "hazard_severity": h_det.source,
                "sensitive_site_proximity": s_det.source,
                "population_exposed": p_det.source,
                "weather_risk": w_det.source,
                "time_outstanding": t_det.source,
                "recurrence": c_det.source,
            }
            for w in [p_warn, w_warn, c_warn]:
                if w:
                    uncertainty_warnings.append(w)

        # 1. Compute Deterministic Physical Risk Score
        factor_inputs_obj = FactorInputs(**factor_dict)
        risk_result = compute_risk_score(factor_inputs_obj, config=config)

        # 2. Evaluate Safety Rules (Independent of physical score)
        safety_eval = evaluate_safety_rules(
            hazard_type=incident.hazard_type,
            factors=factor_dict,
            evidence_status=incident.evidence_status,
            manual_override_data=manual_override_dict,
            config=config
        )

        # 3. Evaluate SLA Status
        sla_result = evaluate_sla_status(
            created_at=incident.created_at,
            sla_deadline=incident.sla_deadline
        )
        if sla_result.escalation_alert:
            uncertainty_warnings.append(sla_result.escalation_alert)

        # Formulate recommended action
        if safety_eval.active:
            recommended_action = f"EMERGENCY OVERRIDE ({safety_eval.effective_severity}): {safety_eval.summary_explanation}"
        elif sla_result.is_breached:
            recommended_action = "URGENT SLA ESCALATION: Incident is overdue. Escalate to supervisor for expedited field assignment."
        elif risk_result.priority_band == "Critical":
            recommended_action = "Immediate priority: Deploy emergency repair crew within 30 minutes."
        elif risk_result.priority_band == "High":
            recommended_action = "High priority: Review and assign field crew within 2 hours."
        elif risk_result.priority_band == "Medium":
            recommended_action = "Medium priority: Schedule inspection in standard daily shift."
        else:
            recommended_action = "Review and assign according to the configured response policy."

        now = datetime.now(timezone.utc)

        effective_priority_band = safety_eval.effective_severity if safety_eval.active else risk_result.priority_band

        # Persist assessment record without overwriting previous assessments
        safety_override_dict = {
            "active": safety_eval.active,
            "effective_severity": safety_eval.effective_severity,
            "triggered_rules": [r.model_dump(mode="json") for r in safety_eval.triggered_rules],
            "manual_override": safety_eval.manual_override,
            "summary": safety_eval.summary_explanation,
        }

        assessment_row = AssessmentModel(
            incident_id=incident_id,
            assessed_at=now,
            risk_score=risk_result.rounded_score,
            priority_band=effective_priority_band,
            formula_version=risk_result.formula_version,
            factor_values=factor_dict,
            factor_contributions=risk_result.factor_contributions,
            factor_sources=factor_sources,
            uncertainty_flags=uncertainty_warnings,
            safety_override=safety_override_dict,
            sla_status=sla_result.sla_status,
            recommended_action=recommended_action,
            explanations=risk_result.explanations,
        )
        db.add(assessment_row)

        audit = AuditLogModel(
            incident_id=incident_id,
            action_type="RISK_ASSESSED",
            details={
                "risk_score": risk_result.rounded_score,
                "priority_band": effective_priority_band,
                "override_active": safety_eval.active,
                "sla_status": sla_result.sla_status,
            },
            actor="ENGINE",
            timestamp=now,
        )
        db.add(audit)
        db.commit()

        return RiskAssessmentResponse(
            incident_id=incident_id,
            risk_score=risk_result.rounded_score,
            priority_band=effective_priority_band,
            safety_override=SafetyOverrideResponse(**safety_override_dict),
            factor_contributions=risk_result.factor_contributions,
            uncertainty_flags=uncertainty_warnings,
            sla_status=sla_result.sla_status,
            sla_deadline=incident.sla_deadline,
            is_sla_breached=sla_result.is_breached,
            explanation=risk_result.explanations,
            recommended_action=recommended_action,
            formula_version=risk_result.formula_version,
            assessed_at=now,
            assigned_department=incident.assigned_department,
        )

    @staticmethod
    def get_latest_assessment(db: Session, incident_id: str) -> RiskAssessmentResponse:
        incident = db.query(IncidentModel).filter(IncidentModel.incident_id == incident_id).first()
        if not incident:
            raise KeyError(f"Incident '{incident_id}' not found.")

        latest = db.query(AssessmentModel).filter(
            AssessmentModel.incident_id == incident_id
        ).order_by(AssessmentModel.assessed_at.desc()).first()

        if not latest:
            # If never assessed, assess now
            return IncidentService.assess_incident(db, incident_id)

        safety_dict = latest.safety_override or {"active": False, "triggered_rules": []}

        return RiskAssessmentResponse(
            incident_id=incident_id,
            risk_score=latest.risk_score,
            priority_band=latest.priority_band,
            safety_override=SafetyOverrideResponse(**safety_dict),
            factor_contributions=latest.factor_contributions,
            uncertainty_flags=latest.uncertainty_flags or [],
            sla_status=latest.sla_status,
            sla_deadline=incident.sla_deadline,
            is_sla_breached=(latest.sla_status == "breached"),
            explanation=latest.explanations or [],
            recommended_action=latest.recommended_action,
            formula_version=latest.formula_version,
            assessed_at=latest.assessed_at,
            assigned_department=incident.assigned_department,
        )

    @staticmethod
    def record_manual_override(
        db: Session,
        incident_id: str,
        authorized_by: str,
        role: str,
        reason: str,
        target_severity: str = "Critical"
    ) -> RiskAssessmentResponse:
        incident = db.query(IncidentModel).filter(IncidentModel.incident_id == incident_id).first()
        if not incident:
            raise KeyError(f"Incident '{incident_id}' not found.")

        valid_roles = ["supervisor", "duty_officer", "admin", "municipal_commissioner"]
        if role.lower() not in valid_roles:
            raise PermissionError(f"Role '{role}' is not authorized to apply manual safety overrides. Required: {valid_roles}")

        # Deactivate any previous overrides
        db.query(ManualOverrideModel).filter(
            ManualOverrideModel.incident_id == incident_id,
            ManualOverrideModel.is_active == True
        ).update({"is_active": False})

        new_override = ManualOverrideModel(
            incident_id=incident_id,
            authorized_by=authorized_by,
            role=role,
            reason=reason,
            target_severity=target_severity,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_override)

        audit = AuditLogModel(
            incident_id=incident_id,
            action_type="MANUAL_OVERRIDE_APPLIED",
            details={
                "authorized_by": authorized_by,
                "role": role,
                "reason": reason,
                "target_severity": target_severity,
            },
            actor=authorized_by,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(audit)
        db.commit()

        # Recalculate assessment with new override active
        return IncidentService.assess_incident(db, incident_id)

    @staticmethod
    def get_priority_queue(db: Session, limit: int = 200) -> List[PriorityQueueItem]:
        incidents = db.query(IncidentModel).all()
        assessment_items: List[Dict[str, Any]] = []

        for inc in incidents:
            latest_assessment = db.query(AssessmentModel).filter(
                AssessmentModel.incident_id == inc.incident_id
            ).order_by(AssessmentModel.assessed_at.desc()).first()

            if not latest_assessment:
                # Assess on the fly
                res = IncidentService.assess_incident(db, inc.incident_id)
                latest_assessment = db.query(AssessmentModel).filter(
                    AssessmentModel.incident_id == inc.incident_id
                ).order_by(AssessmentModel.assessed_at.desc()).first()

            # Build assessment tuple
            safety_dict = latest_assessment.safety_override or {}
            safety_eval = evaluate_safety_rules(
                hazard_type=inc.hazard_type,
                factors=latest_assessment.factor_values or {},
                evidence_status=inc.evidence_status,
                manual_override_data=safety_dict.get("manual_override"),
            )
            # Preserve active override state if manual override was in DB
            if safety_dict.get("active"):
                safety_eval.active = True
                safety_eval.effective_severity = safety_dict.get("effective_severity") or "Critical"
                safety_eval.summary_explanation = safety_dict.get("summary") or "Safety override active"

            factors_obj = FactorInputs(**(latest_assessment.factor_values or {
                "hazard_severity": 0.5, "sensitive_site_proximity": 0.2, "population_exposed": 0.5,
                "weather_risk": 0.5, "time_outstanding": 0.1, "recurrence": 0.0
            }))
            risk_res = compute_risk_score(factors_obj)

            sla_res = evaluate_sla_status(
                created_at=inc.created_at,
                sla_deadline=inc.sla_deadline
            )

            assessment_items.append({
                "incident_id": inc.incident_id,
                "hazard_type": inc.hazard_type,
                "created_at": inc.created_at,
                "evidence_status": inc.evidence_status,
                "assigned_department": inc.assigned_department,
                "risk_result": risk_res,
                "safety_override": safety_eval,
                "sla_result": sla_res,
                "uncertainty_warnings": latest_assessment.uncertainty_flags or [],
            })

        return rank_priority_queue(assessment_items)[:limit]

    @staticmethod
    def get_incident_detail(db: Session, incident_id: str) -> IncidentDetailResponse:
        incident = db.query(IncidentModel).filter(IncidentModel.incident_id == incident_id).first()
        if not incident:
            raise KeyError(f"Incident '{incident_id}' not found.")

        latest_assessment_resp = IncidentService.get_latest_assessment(db, incident_id)

        # Assessment history
        all_assessments = db.query(AssessmentModel).filter(
            AssessmentModel.incident_id == incident_id
        ).order_by(AssessmentModel.assessed_at.desc()).all()

        history_items = [
            AssessmentHistoryItem(
                assessment_id=a.id,
                assessed_at=a.assessed_at,
                risk_score=a.risk_score,
                priority_band=a.priority_band,
                formula_version=a.formula_version,
                factor_values=a.factor_values,
                factor_contributions=a.factor_contributions,
                safety_override=a.safety_override,
                sla_status=a.sla_status,
                recommended_action=a.recommended_action,
                explanations=a.explanations,
            )
            for a in all_assessments
        ]

        # Active manual override
        override_row = db.query(ManualOverrideModel).filter(
            ManualOverrideModel.incident_id == incident_id,
            ManualOverrideModel.is_active == True
        ).first()

        override_dict = None
        if override_row:
            override_dict = {
                "authorized_by": override_row.authorized_by,
                "role": override_row.role,
                "reason": override_row.reason,
                "target_severity": override_row.target_severity,
                "created_at": override_row.created_at.isoformat(),
            }

        # Audit logs
        logs = db.query(AuditLogModel).filter(
            AuditLogModel.incident_id == incident_id
        ).order_by(AuditLogModel.timestamp.desc()).all()

        log_dicts = [
            {
                "id": l.id,
                "action_type": l.action_type,
                "details": l.details,
                "actor": l.actor,
                "timestamp": l.timestamp.isoformat(),
            }
            for l in logs
        ]

        return IncidentDetailResponse(
            incident_id=incident.incident_id,
            hazard_type=incident.hazard_type,
            title=incident.title,
            description=incident.description,
            ward=incident.ward,
            latitude=incident.latitude,
            longitude=incident.longitude,
            created_at=incident.created_at,
            evidence_status=incident.evidence_status,
            sla_deadline=incident.sla_deadline,
            assigned_department=incident.assigned_department,
            latest_assessment=latest_assessment_resp,
            assessment_history=history_items,
            manual_override=override_dict,
            audit_logs=log_dicts,
            ai_reasoning_summary=incident.ai_reasoning_summary,
            ai_model_used=incident.ai_model_used,
            ai_analysis_status=incident.ai_analysis_status,
        )
