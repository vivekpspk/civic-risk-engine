"""
admin_api.py
FastAPI router for administrator controls, priority queue inspection,
dashboard telemetry, worker dispatch & assignment, side-by-side evidence verification,
resolution approval, reopening, and notification history.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.models.database import get_db, IncidentModel
from app.models.schemas import (
    CitizenComplaintResponse, AdminStatusUpdate, AdminAssignmentUpdate,
    AdminDashboardResponse, ManualOverrideRequest, RiskAssessmentResponse,
    AdminAssignWorkerRequest, AdminVerifyResolutionRequest, AdminReopenRequest,
    AdminRejectRequest, WorkerSummaryResponse, IncidentDetailResponse
)
from app.core.priority_engine import PriorityQueueItem
from app.services.complaint_service import ComplaintService
from app.services.incident_service import IncidentService
from app.services.admin_service import AdminService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/api/admin", tags=["Administrator Dashboard & Dispatch"])


@router.get("/priority-queue", response_model=List[PriorityQueueItem])
def get_admin_priority_queue(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Returns the dynamic administrator priority queue:
    1. Active Safety Overrides (Immediate Human Review First)
    2. Physical Risk Score (Highest to lowest)
    3. SLA Status (Breached > Imminent > Within SLA)
    4. Age Tie-Breaker (Oldest unresolved complaints first)
    """
    return IncidentService.get_priority_queue(db, limit=limit)


@router.get("/dashboard", response_model=AdminDashboardResponse)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Returns real-time dashboard telemetry, incident status counts,
    SLA breach alerts, and boundary dispute counts directly from database.
    """
    return ComplaintService.get_admin_dashboard(db)


@router.get("/complaints", response_model=List[CitizenComplaintResponse])
def get_admin_complaints(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lists complaints for administrator dispatch and triage.
    """
    return ComplaintService.list_complaints(db, limit=limit, offset=offset, status_filter=status)


@router.get("/complaints/{complaint_id}")
def get_admin_complaint_detail(complaint_id: str, db: Session = Depends(get_db)):
    """
    Returns complete administrator complaint dossier:
    description, before-and-after evidence, assigned worker, location,
    risk score explanation, SLA deadlines, and audit history.
    """
    try:
        return IncidentService.get_incident_detail(db, complaint_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/complaints/{complaint_id}/assign")
def assign_worker_to_complaint(
    complaint_id: str,
    req: AdminAssignWorkerRequest,
    db: Session = Depends(get_db)
):
    """
    Administrator assigns a municipal field worker to resolve a complaint.
    Transitions status to ASSIGNED and records assignment instructions.
    """
    try:
        return AdminService.assign_worker(db, complaint_id, req)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/complaints/{complaint_id}/verify-resolution")
def verify_complaint_resolution(
    complaint_id: str,
    req: AdminVerifyResolutionRequest,
    db: Session = Depends(get_db)
):
    """
    Administrator verifies completion photos:
    - If approved: transitions to COMPLETED, records verification timestamp, and triggers citizen SMS.
    - If rejected: records reason and returns task to IN_PROGRESS.
    """
    try:
        return AdminService.verify_resolution(db, complaint_id, req)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/complaints/{complaint_id}/reopen")
def reopen_complaint(
    complaint_id: str,
    req: AdminReopenRequest,
    db: Session = Depends(get_db)
):
    """
    Administrator reopens an inadequate or recurring resolution: transitions to REOPENED.
    """
    try:
        return AdminService.reopen_complaint(db, complaint_id, req)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/complaints/{complaint_id}/reject")
def reject_complaint(
    complaint_id: str,
    req: AdminRejectRequest,
    db: Session = Depends(get_db)
):
    """
    Administrator rejects a complaint with a mandatory reason: transitions to REJECTED.
    """
    try:
        return AdminService.reject_complaint(db, complaint_id, req)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/workers", response_model=List[WorkerSummaryResponse])
def list_municipal_workers(db: Session = Depends(get_db)):
    """
    Lists all registered field workers, their department, ward, and active task load.
    """
    return AdminService.list_workers(db)


@router.get("/notifications")
def list_notification_history(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Returns the SMS notification history and delivery statuses for audit inspection.
    """
    return NotificationService.list_notifications(db, limit=limit)


@router.patch("/complaints/{complaint_id}/status", response_model=CitizenComplaintResponse)
def update_complaint_status(
    complaint_id: str,
    req: AdminStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Allows authorized administrators to verify reports, mark work in progress,
    or record confirmed resolution with notes.
    """
    try:
        return ComplaintService.update_complaint_status(db, complaint_id, req)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/complaints/{complaint_id}/assignment", response_model=CitizenComplaintResponse)
def update_complaint_assignment(
    complaint_id: str,
    req: AdminAssignmentUpdate,
    db: Session = Depends(get_db)
):
    """
    Reassigns complaint department or ward, resolving boundary disputes with mandatory reason logging.
    """
    try:
        return ComplaintService.update_complaint_assignment(db, complaint_id, req)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/complaints/{complaint_id}/override", response_model=RiskAssessmentResponse)
def apply_admin_manual_override(
    complaint_id: str,
    req: ManualOverrideRequest,
    db: Session = Depends(get_db)
):
    """
    Applies an authorized manual safety override to promote a complaint's priority.
    Requires role authorization (supervisor, duty_officer, admin, municipal_commissioner) and documented reason.
    """
    try:
        return IncidentService.record_manual_override(
            db=db,
            incident_id=complaint_id,
            authorized_by=req.authorized_by,
            role=req.role,
            reason=req.reason,
            target_severity=req.target_severity,
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
