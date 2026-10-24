"""
public_api.py
FastAPI router for Public Citizen Tracking & Status Verification.
Provides an unauthenticated, rate-limited public tracking portal where citizens
can inspect the live status of their complaint, view approved before-and-after photos,
and check resolution progress WITHOUT exposing any private reporter details or internal notes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas import PublicComplaintTrackingResponse
from app.services.complaint_service import ComplaintService

router = APIRouter(prefix="/api/public", tags=["Citizen Public Tracking"])


@router.get("/complaints/{public_complaint_id}", response_model=PublicComplaintTrackingResponse)
def get_public_complaint_tracking(
    public_complaint_id: str,
    db: Session = Depends(get_db)
):
    """
    Public Status & Evidence Tracking:
    Displays status timeline, privacy-approved before-and-after photos,
    and verified resolution descriptions.
    Guarantees privacy: reporter phone, email, worker contact, and internal notes are never returned.
    """
    try:
        return ComplaintService.get_public_tracking_dossier(db, public_complaint_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
