"""
admin_api.py
FastAPI router for administrator controls, priority queue inspection,
dashboard telemetry, department re-routing, and authorized safety overrides.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas import (
    CitizenComplaintResponse, AdminStatusUpdate, AdminAssignmentUpdate,
    AdminDashboardResponse, ManualOverrideRequest, RiskAssessmentResponse
)
from app.core.priority_engine import PriorityQueueItem
from app.services.complaint_service import ComplaintService
from app.services.incident_service import IncidentService

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
