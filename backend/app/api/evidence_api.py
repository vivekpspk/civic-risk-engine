"""
evidence_api.py
FastAPI router for Evidence Upload, Retrieval, and Side-by-Side Comparison.
Provides separate endpoints for citizen 'before' photos and worker 'after' photos,
MIME verification, EXIF stripping, and safe file streaming.
"""

import base64
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Header, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db, EvidenceModel, IncidentModel
from app.services.evidence_service import EvidenceService
from app.services.storage_service import active_storage_provider

router = APIRouter(tags=["Evidence Management & Before-and-After Comparison"])


class JsonEvidenceUpload(BaseModel):
    file_base64: str
    original_filename: str = "upload.jpg"
    mime_type: str = "image/jpeg"
    caption: Optional[str] = None
    uploaded_by_id: Optional[str] = None


@router.post("/api/complaints/{complaint_id}/evidence/before", status_code=status.HTTP_201_CREATED)
async def upload_before_evidence(
    complaint_id: str,
    file: Optional[UploadFile] = File(None),
    json_body: Optional[JsonEvidenceUpload] = None,
    caption: Optional[str] = Form(None),
    citizen_name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Citizen Upload Before-Photo:
    Accepts multipart file upload or JSON base64.
    Strips EXIF, checks MIME signatures, and saves as 'before' evidence.
    """
    complaint = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Complaint '{complaint_id}' not found.")

    try:
        if file is not None:
            raw_bytes = await file.read()
            filename = file.filename or "citizen_before.jpg"
            mime = file.content_type or "image/jpeg"
            uploader = citizen_name or complaint.reporter_name or "citizen"
            cap = caption
        elif json_body is not None:
            raw_bytes = base64.b64decode(json_body.file_base64.split(",")[-1])
            filename = json_body.original_filename
            mime = json_body.mime_type
            uploader = json_body.uploaded_by_id or complaint.reporter_name or "citizen"
            cap = json_body.caption
        else:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No file or base64 evidence payload provided.")

        record = EvidenceService.process_and_store_evidence(
            db=db,
            complaint_id=complaint_id,
            file_bytes=raw_bytes,
            original_filename=filename,
            declared_mime=mime,
            evidence_type="before",
            uploaded_by_role="citizen",
            uploaded_by_id=uploader,
            caption=cap
        )
        return {
            "evidence_id": record.evidence_id,
            "complaint_id": complaint_id,
            "evidence_type": "before",
            "original_filename": record.original_filename,
            "file_size_bytes": record.file_size_bytes,
            "view_url": f"/api/evidence/{record.evidence_id}/file",
            "message": "Before photo uploaded, stripped of EXIF, and securely registered."
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/api/worker/complaints/{complaint_id}/evidence/after", status_code=status.HTTP_201_CREATED)
async def upload_after_evidence(
    complaint_id: str,
    file: Optional[UploadFile] = File(None),
    json_body: Optional[JsonEvidenceUpload] = None,
    worker_id: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    x_worker_id: Optional[str] = Header(None, alias="X-Worker-ID"),
    db: Session = Depends(get_db)
):
    """
    Worker Upload After-Photo:
    Accepts multipart file upload or JSON base64.
    Strips EXIF, checks MIME signatures, and saves as 'after' evidence.
    """
    complaint = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Complaint '{complaint_id}' not found.")

    eff_worker = worker_id or x_worker_id or (json_body.uploaded_by_id if json_body else None)
    if not eff_worker:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Worker ID is required to upload after-evidence.")

    try:
        if file is not None:
            raw_bytes = await file.read()
            filename = file.filename or "worker_after.jpg"
            mime = file.content_type or "image/jpeg"
            cap = caption
        elif json_body is not None:
            raw_bytes = base64.b64decode(json_body.file_base64.split(",")[-1])
            filename = json_body.original_filename
            mime = json_body.mime_type
            cap = json_body.caption
        else:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No file or base64 evidence payload provided.")

        record = EvidenceService.process_and_store_evidence(
            db=db,
            complaint_id=complaint_id,
            file_bytes=raw_bytes,
            original_filename=filename,
            declared_mime=mime,
            evidence_type="after",
            uploaded_by_role="worker",
            uploaded_by_id=eff_worker,
            caption=cap
        )
        return {
            "evidence_id": record.evidence_id,
            "complaint_id": complaint_id,
            "evidence_type": "after",
            "original_filename": record.original_filename,
            "file_size_bytes": record.file_size_bytes,
            "view_url": f"/api/evidence/{record.evidence_id}/file",
            "message": "After resolution photo uploaded and linked to complaint."
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/api/complaints/{complaint_id}/comparison")
def get_before_after_comparison(complaint_id: str, db: Session = Depends(get_db)):
    """
    Side-by-Side Comparison Contract:
    Returns strictly separated before_evidence and after_evidence collections
    along with resolution summary for administrator verification.
    """
    try:
        return EvidenceService.get_comparison(db, complaint_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/api/complaints/{complaint_id}/evidence")
def list_complaint_evidence(complaint_id: str, db: Session = Depends(get_db)):
    """
    Lists all evidence records associated with the complaint.
    """
    records = (
        db.query(EvidenceModel)
        .filter(EvidenceModel.complaint_id == complaint_id)
        .order_by(EvidenceModel.uploaded_at.asc())
        .all()
    )
    return [
        {
            "evidence_id": r.evidence_id,
            "complaint_id": r.complaint_id,
            "evidence_type": r.evidence_type,
            "original_filename": r.original_filename,
            "mime_type": r.mime_type,
            "file_size_bytes": r.file_size_bytes,
            "uploaded_by_role": r.uploaded_by_role,
            "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else "",
            "view_url": f"/api/evidence/{r.evidence_id}/file",
            "redaction_status": r.redaction_status
        }
        for r in records
    ]


@router.get("/api/evidence/{evidence_id}/file")
def get_evidence_file(evidence_id: str, db: Session = Depends(get_db)):
    """
    Safe file streaming endpoint:
    Returns clean, EXIF-stripped image bytes with appropriate Content-Type.
    Never exposes internal filesystem paths or directory structure.
    """
    record = db.query(EvidenceModel).filter(EvidenceModel.evidence_id == evidence_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")

    try:
        file_bytes, mime_type = active_storage_provider.get_file(record.file_path)
        return Response(content=file_bytes, media_type=mime_type)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence storage file missing.")
