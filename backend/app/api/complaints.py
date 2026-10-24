"""
complaints.py
FastAPI router for citizen complaint intake, public status tracking,
reassessments, and assessment history.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas import (
    CitizenComplaintCreate, CitizenComplaintResponse, RiskAssessmentResponse,
    AssessmentHistoryItem, AssessIncidentRequest
)
from app.services.complaint_service import ComplaintService
from app.services.incident_service import IncidentService

router = APIRouter(prefix="/api/complaints", tags=["Citizen Complaints & Triage"])


@router.post("", response_model=CitizenComplaintResponse, status_code=status.HTTP_201_CREATED)
@router.post("/submit", response_model=CitizenComplaintResponse, status_code=status.HTTP_201_CREATED)
def submit_complaint(req: CitizenComplaintCreate, db: Session = Depends(get_db)):
    """
    Automatic Citizen Complaint Intake:
    Accepts description, optional GPS coordinates, optional category hint, and evidence.
    Automatically classifies hazard, extracts sensitive-site proximity, estimates population exposure,
    integrates weather, computes risk score, applies safety rules, determines ward & department,
    and returns a unique complaint ID with estimated SLA and priority.
    """
    try:
        return ComplaintService.submit_citizen_complaint(db, req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{complaint_id}", response_model=CitizenComplaintResponse)
def get_complaint_status(complaint_id: str, db: Session = Depends(get_db)):
    """
    Public Status Tracking:
    Returns the real-time status, assessed priority, and plain-language explanation.
    Never exposes private reporter contact information (phone, email, real identity).
    """
    try:
        return ComplaintService.get_public_complaint(db, complaint_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("", response_model=List[CitizenComplaintResponse])
def list_complaints(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lists recent civic complaints with optional status filtering.
    """
    return ComplaintService.list_complaints(db, limit=limit, offset=offset, status_filter=status)


@router.post("/{complaint_id}/assess", response_model=RiskAssessmentResponse)
def reassess_complaint(
    complaint_id: str,
    req: Optional[AssessIncidentRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Reassesses an existing complaint when new evidence, weather, or location data arrives.
    """
    try:
        return IncidentService.assess_incident(db, complaint_id, req)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{complaint_id}/risk", response_model=RiskAssessmentResponse)
def get_complaint_risk(complaint_id: str, db: Session = Depends(get_db)):
    """
    Returns the active risk score and factor contribution breakdown for the specified complaint.
    """
    try:
        return IncidentService.get_latest_assessment(db, complaint_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{complaint_id}/history", response_model=List[AssessmentHistoryItem])
def get_complaint_history(complaint_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the complete immutable audit trail of prior assessments for the complaint.
    """
    try:
        detail = IncidentService.get_incident_detail(db, complaint_id)
        return detail.assessment_history
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
