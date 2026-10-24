"""
incidents.py
FastAPI router for incident creation, risk assessment, retrieval,
assessment history, and authorized manual overrides.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas import (
    CreateIncidentRequest, AssessIncidentRequest, RiskAssessmentResponse,
    IncidentDetailResponse, AssessmentHistoryItem, ManualOverrideRequest
)
from app.services.incident_service import IncidentService

router = APIRouter(prefix="/incidents", tags=["Incidents & Risk Assessment"])


@router.post("", response_model=RiskAssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(req: CreateIncidentRequest, db: Session = Depends(get_db)):
    """
    Creates a new municipal incident and automatically runs initial risk assessment.
    """
    try:
        IncidentService.create_incident(db, req)
        return IncidentService.get_latest_assessment(db, req.incident_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{incident_id}/assess", response_model=RiskAssessmentResponse)
def assess_incident(incident_id: str, req: AssessIncidentRequest, db: Session = Depends(get_db)):
    """
    Calculates or recalculates the deterministic physical risk score,
    safety overrides, and SLA status for the specified incident.
    """
    try:
        return IncidentService.assess_incident(db, incident_id, req)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{incident_id}/risk", response_model=RiskAssessmentResponse)
def get_incident_risk(incident_id: str, db: Session = Depends(get_db)):
    """
    Returns the latest risk assessment for the specified incident.
    """
    try:
        return IncidentService.get_latest_assessment(db, incident_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident_detail(incident_id: str, db: Session = Depends(get_db)):
    """
    Returns complete incident details, factor-level breakdown, audit logs,
    and full assessment history.
    """
    try:
        return IncidentService.get_incident_detail(db, incident_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{incident_id}/history", response_model=List[AssessmentHistoryItem])
def get_incident_history(incident_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the complete immutable historical trail of risk assessments
    for the specified incident. Never overwrites prior assessments.
    """
    try:
        detail = IncidentService.get_incident_detail(db, incident_id)
        return detail.assessment_history
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{incident_id}/override", response_model=RiskAssessmentResponse)
def apply_manual_override(incident_id: str, req: ManualOverrideRequest, db: Session = Depends(get_db)):
    """
    Applies an authorized manual safety override to promote an incident's priority.
    Requires role authorization (supervisor, duty_officer, admin) and a recorded reason.
    """
    try:
        return IncidentService.record_manual_override(
            db=db,
            incident_id=incident_id,
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
