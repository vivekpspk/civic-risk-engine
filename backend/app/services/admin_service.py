"""
admin_service.py
Administrator Operations & Verification Service for IMPACTX 2026.
Handles worker assignment, side-by-side evidence verification, resolution approval,
reopening inadequate repairs, rejection with documented reasons, and citizen SMS triggering.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.database import (
    IncidentModel, WorkerModel, AssignmentModel, ResolutionSubmissionModel,
    EvidenceModel, AuditLogModel, StatusHistoryModel
)
from app.models.schemas import (
    AdminAssignWorkerRequest, AdminVerifyResolutionRequest, AdminReopenRequest,
    AdminRejectRequest, WorkerSummaryResponse
)
from app.core.lifecycle import (
    ComplaintLifecycleStatus, validate_transition, record_status_history, normalize_status
)
from app.services.notification_service import NotificationService


class AdminService:
    @staticmethod
    def list_workers(db: Session) -> List[WorkerSummaryResponse]:
        """Returns all municipal workers and their current workload."""
        workers = db.query(WorkerModel).all()
        return [
            WorkerSummaryResponse(
                worker_id=w.worker_id,
                name=w.name,
                phone=w.phone,
                department=w.department,
                ward=w.ward,
                status=w.status,
                active_tasks_count=w.active_tasks_count
            )
            for w in workers
        ]

    @staticmethod
    def assign_worker(db: Session, complaint_id: str, req: AdminAssignWorkerRequest) -> Dict[str, any]:
        """
        Administrator assigns a field worker to a complaint.
        Transitions complaint status to ASSIGNED.
        """
        complaint = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
        if not complaint:
            raise KeyError(f"Complaint '{complaint_id}' not found.")

        worker = db.query(WorkerModel).filter(WorkerModel.worker_id == req.worker_id).first()
        if not worker:
            raise KeyError(f"Worker '{req.worker_id}' does not exist in municipal roster.")

        valid, err = validate_transition(
            current_status=complaint.status,
            target_status=ComplaintLifecycleStatus.ASSIGNED.value,
            actor_role="administrator",
            is_admin=True
        )
        if not valid:
            raise ValueError(err)

        # Create Assignment record
        assignment = AssignmentModel(
            complaint_id=complaint_id,
            worker_id=req.worker_id,
            assigned_by_admin=req.admin_id,
            assigned_at=datetime.now(timezone.utc),
            instructions=req.instructions,
            target_completion_time=req.target_completion_time,
            status="assigned"
        )
        db.add(assignment)

        # Update complaint and worker active tasks
        complaint.current_worker_id = req.worker_id
        complaint.status = ComplaintLifecycleStatus.ASSIGNED.value
        worker.active_tasks_count += 1

        record_status_history(
            db=db,
            complaint_id=complaint_id,
            previous_status=complaint.status,
            new_status=ComplaintLifecycleStatus.ASSIGNED.value,
            actor_id=req.admin_id,
            actor_role="administrator",
            notes=f"Assigned to {worker.name} ({worker.worker_id}) by admin {req.admin_id}. Instructions: {req.instructions or 'None'}"
        )
        db.commit()
        return {
            "complaint_id": complaint_id,
            "status": complaint.status,
            "worker_id": req.worker_id,
            "worker_name": worker.name,
            "instructions": req.instructions,
            "message": f"Successfully assigned to worker {worker.name}."
        }

    @staticmethod
    def verify_resolution(db: Session, complaint_id: str, req: AdminVerifyResolutionRequest) -> Dict[str, any]:
        """
        Administrator compares before/after photos and approves (COMPLETED) or rejects (IN_PROGRESS) resolution.
        On approval: triggers SMS notification to citizen.
        """
        complaint = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
        if not complaint:
            raise KeyError(f"Complaint '{complaint_id}' not found.")

        latest_res = (
            db.query(ResolutionSubmissionModel)
            .filter(ResolutionSubmissionModel.complaint_id == complaint_id)
            .order_by(ResolutionSubmissionModel.submitted_at.desc())
            .first()
        )
        if not latest_res:
            raise ValueError(f"No resolution submission found for complaint '{complaint_id}' to verify.")

        # Check after photos exist
        after_photos = (
            db.query(EvidenceModel)
            .filter(EvidenceModel.complaint_id == complaint_id)
            .filter(EvidenceModel.evidence_type == "after")
            .all()
        )
        has_after = len(after_photos) > 0

        decision = req.decision.strip().lower()

        if decision == "approve":
            valid, err = validate_transition(
                current_status=complaint.status,
                target_status=ComplaintLifecycleStatus.COMPLETED.value,
                actor_role="administrator",
                has_after_evidence=has_after,
                is_admin=True
            )
            if not valid:
                raise ValueError(err)

            complaint.status = ComplaintLifecycleStatus.COMPLETED.value
            complaint.resolved_at = datetime.now(timezone.utc)
            latest_res.verification_status = "verified"
            latest_res.verified_by_admin = req.admin_id
            latest_res.verified_at = datetime.now(timezone.utc)
            latest_res.verification_notes = req.notes or "Resolution approved by administrator."

            # Update assignment
            if complaint.assignments:
                complaint.assignments[0].status = "completed"

            # Decrement worker active tasks
            if complaint.current_worker_id:
                w = db.query(WorkerModel).filter(WorkerModel.worker_id == complaint.current_worker_id).first()
                if w and w.active_tasks_count > 0:
                    w.active_tasks_count -= 1

            record_status_history(
                db=db,
                complaint_id=complaint_id,
                previous_status=ComplaintLifecycleStatus.VERIFICATION_REQUIRED.value,
                new_status=ComplaintLifecycleStatus.COMPLETED.value,
                actor_id=req.admin_id,
                actor_role="administrator",
                notes=f"Resolution verified & approved by {req.admin_id}. Proof photos accepted."
            )
            db.commit()

            # Trigger SMS notification to citizen
            sms_result = NotificationService.send_resolution_completion_sms(db, complaint_id)

            return {
                "complaint_id": complaint_id,
                "status": complaint.status,
                "verification_status": "verified",
                "verified_by_admin": req.admin_id,
                "resolved_at": complaint.resolved_at.isoformat(),
                "notification_result": sms_result.model_dump(),
                "message": "Resolution verified and marked COMPLETED. Citizen notification triggered."
            }

        elif decision == "reject":
            if not req.notes or len(req.notes.strip()) < 5:
                raise ValueError("A specific reason of at least 5 characters is required when rejecting a resolution.")

            valid, err = validate_transition(
                current_status=complaint.status,
                target_status=ComplaintLifecycleStatus.IN_PROGRESS.value,
                actor_role="administrator",
                is_admin=True
            )
            if not valid:
                raise ValueError(err)

            complaint.status = ComplaintLifecycleStatus.IN_PROGRESS.value
            latest_res.verification_status = "rejected"
            latest_res.verified_by_admin = req.admin_id
            latest_res.verified_at = datetime.now(timezone.utc)
            latest_res.verification_notes = req.notes

            if complaint.assignments:
                complaint.assignments[0].status = "in_progress"

            record_status_history(
                db=db,
                complaint_id=complaint_id,
                previous_status=ComplaintLifecycleStatus.VERIFICATION_REQUIRED.value,
                new_status=ComplaintLifecycleStatus.IN_PROGRESS.value,
                actor_id=req.admin_id,
                actor_role="administrator",
                notes=f"Resolution rejected by {req.admin_id}. Reason: {req.notes}. Returned to worker."
            )
            db.commit()

            return {
                "complaint_id": complaint_id,
                "status": complaint.status,
                "verification_status": "rejected",
                "rejection_notes": req.notes,
                "message": "Resolution rejected. Task returned to assigned worker for rework."
            }
        else:
            raise ValueError(f"Invalid verification decision '{req.decision}'. Must be 'approve' or 'reject'.")

    @staticmethod
    def reopen_complaint(db: Session, complaint_id: str, req: AdminReopenRequest) -> Dict[str, any]:
        """
        Administrator reopens an inadequate or recurring resolution: transitions to REOPENED.
        """
        complaint = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
        if not complaint:
            raise KeyError(f"Complaint '{complaint_id}' not found.")

        valid, err = validate_transition(
            current_status=complaint.status,
            target_status=ComplaintLifecycleStatus.REOPENED.value,
            actor_role="administrator",
            is_admin=True
        )
        if not valid:
            raise ValueError(err)

        complaint.status = ComplaintLifecycleStatus.REOPENED.value
        complaint.reopened_count = getattr(complaint, "reopened_count", 0) + 1

        record_status_history(
            db=db,
            complaint_id=complaint_id,
            previous_status=ComplaintLifecycleStatus.COMPLETED.value,
            new_status=ComplaintLifecycleStatus.REOPENED.value,
            actor_id=req.admin_id,
            actor_role="administrator",
            notes=f"Complaint reopened by admin {req.admin_id}. Reason: {req.reason}"
        )
        db.commit()
        return {
            "complaint_id": complaint_id,
            "status": complaint.status,
            "reopened_count": complaint.reopened_count,
            "reason": req.reason,
            "message": "Complaint reopened successfully. Returned to administrative queue."
        }

    @staticmethod
    def reject_complaint(db: Session, complaint_id: str, req: AdminRejectRequest) -> Dict[str, any]:
        """
        Administrator rejects a complaint: transitions to REJECTED with mandatory reason.
        """
        complaint = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
        if not complaint:
            raise KeyError(f"Complaint '{complaint_id}' not found.")

        valid, err = validate_transition(
            current_status=complaint.status,
            target_status=ComplaintLifecycleStatus.REJECTED.value,
            actor_role="administrator",
            is_admin=True
        )
        if not valid:
            raise ValueError(err)

        complaint.status = ComplaintLifecycleStatus.REJECTED.value
        complaint.rejection_reason = req.reason

        record_status_history(
            db=db,
            complaint_id=complaint_id,
            previous_status=complaint.status,
            new_status=ComplaintLifecycleStatus.REJECTED.value,
            actor_id=req.admin_id,
            actor_role="administrator",
            notes=f"Complaint rejected by admin {req.admin_id}. Reason: {req.reason}"
        )
        db.commit()
        return {
            "complaint_id": complaint_id,
            "status": complaint.status,
            "rejection_reason": req.reason,
            "message": "Complaint rejected."
        }
