"""
worker_service.py
Field Worker Operations & Workflow Service for IMPACTX 2026.
Handles task assignments, acceptance, work in progress, blocker reporting,
and resolution submissions with after-evidence validation.
Enforces the strict rule that workers cannot approve or complete their own tasks.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.database import (
    IncidentModel, WorkerModel, AssignmentModel, ResolutionSubmissionModel,
    EvidenceModel, AuditLogModel
)
from app.models.schemas import (
    WorkerTaskResponse, WorkerResolutionSubmitRequest
)
from app.core.lifecycle import (
    ComplaintLifecycleStatus, validate_transition, record_status_history, normalize_status
)


class WorkerService:
    @staticmethod
    def get_assigned_tasks(db: Session, worker_id: str) -> List[WorkerTaskResponse]:
        """
        Retrieves all active or pending tasks assigned to the specified worker.
        """
        assignments = (
            db.query(AssignmentModel)
            .filter(AssignmentModel.worker_id == worker_id)
            .order_by(AssignmentModel.assigned_at.desc())
            .all()
        )

        results = []
        for a in assignments:
            inc = db.query(IncidentModel).filter(IncidentModel.incident_id == a.complaint_id).first()
            if not inc:
                continue

            # Fetch latest assessment for priority
            score = 50.0
            p_band = "Medium"
            safety_override = False
            if inc.assessments:
                latest = inc.assessments[0]
                score = latest.risk_score
                p_band = latest.priority_band
                safety_override = latest.safety_override.get("active", False)

            results.append(WorkerTaskResponse(
                task_id=a.id,
                complaint_id=a.complaint_id,
                worker_id=a.worker_id,
                status=a.status,
                assigned_at=a.assigned_at.isoformat() if a.assigned_at else "",
                instructions=a.instructions,
                target_completion_time=a.target_completion_time.isoformat() if a.target_completion_time else None,
                hazard_title=inc.title or inc.hazard_type,
                ward=inc.ward or "Ward 07",
                latitude=inc.latitude,
                longitude=inc.longitude,
                location_address=inc.location_address,
                priority_band=p_band,
                risk_score=score,
                safety_override_active=safety_override
            ))
        return results

    @staticmethod
    def accept_task(db: Session, complaint_id: str, worker_id: str, notes: Optional[str] = None) -> Dict[str, any]:
        """
        Assigned worker accepts the task: transitions ASSIGNED -> ACCEPTED.
        """
        complaint = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
        if not complaint:
            raise KeyError(f"Complaint '{complaint_id}' not found.")

        # Check worker authorization
        assignment = (
            db.query(AssignmentModel)
            .filter(AssignmentModel.complaint_id == complaint_id)
            .order_by(AssignmentModel.assigned_at.desc())
            .first()
        )
        if not assignment or assignment.worker_id != worker_id:
            raise PermissionError(f"Worker '{worker_id}' is not assigned to complaint '{complaint_id}'.")

        # Validate transition
        valid, err = validate_transition(
            current_status=complaint.status,
            target_status=ComplaintLifecycleStatus.ACCEPTED.value,
            actor_role="worker",
            is_assigned_worker=True
        )
        if not valid:
            raise ValueError(err)

        complaint.status = ComplaintLifecycleStatus.ACCEPTED.value
        assignment.status = "accepted"

        record_status_history(
            db=db,
            complaint_id=complaint_id,
            previous_status=ComplaintLifecycleStatus.ASSIGNED.value,
            new_status=ComplaintLifecycleStatus.ACCEPTED.value,
            actor_id=worker_id,
            actor_role="worker",
            notes=notes or f"Task accepted by assigned worker {worker_id}."
        )
        db.commit()
        return {
            "complaint_id": complaint_id,
            "status": complaint.status,
            "worker_id": worker_id,
            "message": "Task accepted successfully."
        }

    @staticmethod
    def start_work(db: Session, complaint_id: str, worker_id: str, inspection_notes: Optional[str] = None) -> Dict[str, any]:
        """
        Worker commences on-site inspection or repair: transitions ACCEPTED -> IN_PROGRESS.
        """
        complaint = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
        if not complaint:
            raise KeyError(f"Complaint '{complaint_id}' not found.")

        assignment = (
            db.query(AssignmentModel)
            .filter(AssignmentModel.complaint_id == complaint_id)
            .order_by(AssignmentModel.assigned_at.desc())
            .first()
        )
        if not assignment or assignment.worker_id != worker_id:
            raise PermissionError(f"Worker '{worker_id}' is not assigned to complaint '{complaint_id}'.")

        valid, err = validate_transition(
            current_status=complaint.status,
            target_status=ComplaintLifecycleStatus.IN_PROGRESS.value,
            actor_role="worker",
            is_assigned_worker=True
        )
        if not valid:
            raise ValueError(err)

        complaint.status = ComplaintLifecycleStatus.IN_PROGRESS.value
        assignment.status = "in_progress"

        record_status_history(
            db=db,
            complaint_id=complaint_id,
            previous_status=ComplaintLifecycleStatus.ACCEPTED.value,
            new_status=ComplaintLifecycleStatus.IN_PROGRESS.value,
            actor_id=worker_id,
            actor_role="worker",
            notes=inspection_notes or f"Worker {worker_id} arrived at location and commenced repairs."
        )
        db.commit()
        return {
            "complaint_id": complaint_id,
            "status": complaint.status,
            "worker_id": worker_id,
            "message": "Work marked in progress."
        }

    @staticmethod
    def report_unable_to_resolve(db: Session, complaint_id: str, worker_id: str, reason: str) -> Dict[str, any]:
        """
        Worker reports a genuine blocker: transitions to UNABLE_TO_RESOLVE.
        """
        complaint = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
        if not complaint:
            raise KeyError(f"Complaint '{complaint_id}' not found.")

        assignment = (
            db.query(AssignmentModel)
            .filter(AssignmentModel.complaint_id == complaint_id)
            .order_by(AssignmentModel.assigned_at.desc())
            .first()
        )
        if not assignment or assignment.worker_id != worker_id:
            raise PermissionError(f"Worker '{worker_id}' is not assigned to complaint '{complaint_id}'.")

        valid, err = validate_transition(
            current_status=complaint.status,
            target_status=ComplaintLifecycleStatus.UNABLE_TO_RESOLVE.value,
            actor_role="worker",
            is_assigned_worker=True
        )
        if not valid:
            raise ValueError(err)

        complaint.status = ComplaintLifecycleStatus.UNABLE_TO_RESOLVE.value
        complaint.blocker_reason = reason
        assignment.status = "unable_to_resolve"

        record_status_history(
            db=db,
            complaint_id=complaint_id,
            previous_status=complaint.status,
            new_status=ComplaintLifecycleStatus.UNABLE_TO_RESOLVE.value,
            actor_id=worker_id,
            actor_role="worker",
            notes=f"Blocker reported: {reason}"
        )
        db.commit()
        return {
            "complaint_id": complaint_id,
            "status": complaint.status,
            "worker_id": worker_id,
            "blocker_reason": reason,
            "message": "Blocker reported. Complaint requires administrator escalation."
        }

    @staticmethod
    def submit_resolution(db: Session, complaint_id: str, req: WorkerResolutionSubmitRequest) -> Dict[str, any]:
        """
        Worker submits completion details and after-photos.
        Transitions complaint to VERIFICATION_REQUIRED for administrator review.
        Enforces rule that worker submission CANNOT mark task as COMPLETED.
        """
        complaint = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
        if not complaint:
            raise KeyError(f"Complaint '{complaint_id}' not found.")

        assignment = (
            db.query(AssignmentModel)
            .filter(AssignmentModel.complaint_id == complaint_id)
            .order_by(AssignmentModel.assigned_at.desc())
            .first()
        )
        if not assignment or assignment.worker_id != req.worker_id:
            raise PermissionError(f"Worker '{req.worker_id}' is not authorized to submit resolution for '{complaint_id}'.")

        # Verify that at least one valid after-photo evidence ID was provided
        if not req.after_evidence_ids or len(req.after_evidence_ids) == 0:
            raise ValueError("Resolution submission requires at least one after-photo evidence upload.")

        existing_evidence = (
            db.query(EvidenceModel)
            .filter(EvidenceModel.complaint_id == complaint_id)
            .filter(EvidenceModel.evidence_id.in_(req.after_evidence_ids))
            .filter(EvidenceModel.evidence_type == "after")
            .all()
        )
        if len(existing_evidence) == 0:
            raise ValueError(
                f"No valid after-photo evidence found matching IDs {req.after_evidence_ids} for complaint '{complaint_id}'."
            )

        valid, err = validate_transition(
            current_status=complaint.status,
            target_status=ComplaintLifecycleStatus.VERIFICATION_REQUIRED.value,
            actor_role="worker",
            has_after_evidence=True,
            is_assigned_worker=True
        )
        if not valid:
            raise ValueError(err)

        # Record resolution submission
        res_record = ResolutionSubmissionModel(
            complaint_id=complaint_id,
            worker_id=req.worker_id,
            description=req.description,
            action_taken=req.action_taken,
            submitted_at=datetime.now(timezone.utc),
            completion_latitude=req.completion_latitude,
            completion_longitude=req.completion_longitude,
            blockers=req.blockers,
            after_evidence_ids=req.after_evidence_ids,
            verification_status="pending"
        )
        db.add(res_record)

        complaint.status = ComplaintLifecycleStatus.VERIFICATION_REQUIRED.value
        complaint.resolution_notes = req.description

        record_status_history(
            db=db,
            complaint_id=complaint_id,
            previous_status=ComplaintLifecycleStatus.IN_PROGRESS.value,
            new_status=ComplaintLifecycleStatus.VERIFICATION_REQUIRED.value,
            actor_id=req.worker_id,
            actor_role="worker",
            notes=f"Resolution submitted: {req.action_taken}. Awaiting administrator verification."
        )
        db.commit()
        db.refresh(res_record)

        return {
            "complaint_id": complaint_id,
            "status": complaint.status,
            "verification_status": "pending",
            "after_evidence_count": len(existing_evidence),
            "message": "Resolution submitted successfully. Awaiting administrator verification."
        }
