"""
worker_api.py
FastAPI router for Field Worker Operations & Mobile App Interop.
Allows assigned municipal workers to view tasks, accept assignments,
mark work in progress, report obstacles, and submit resolution reports.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session

from app.models.database import get_db, IncidentModel, AssignmentModel
from app.models.schemas import (
    WorkerTaskResponse, WorkerAcceptRequest, WorkerStartRequest,
    WorkerUnableToResolveRequest, WorkerResolutionSubmitRequest
)
from app.services.worker_service import WorkerService

router = APIRouter(prefix="/api/worker", tags=["Field Worker Operations"])


@router.get("/tasks", response_model=List[WorkerTaskResponse])
def get_worker_tasks(
    worker_id: Optional[str] = Query(None, description="Worker identifier"),
    x_worker_id: Optional[str] = Header(None, alias="X-Worker-ID"),
    db: Session = Depends(get_db)
):
    """
    Field Worker Task Dashboard:
    Returns the list of civic incidents assigned to this worker.
    Requires worker identification via query parameter or 'X-Worker-ID' header.
    """
    effective_id = worker_id or x_worker_id
    if not effective_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Worker ID must be provided via query parameter '?worker_id=' or header 'X-Worker-ID'."
        )
    return WorkerService.get_assigned_tasks(db, effective_id)


@router.get("/tasks/{complaint_id}")
def get_worker_task_detail(
    complaint_id: str,
    worker_id: Optional[str] = Query(None),
    x_worker_id: Optional[str] = Header(None, alias="X-Worker-ID"),
    db: Session = Depends(get_db)
):
    """
    Returns specific task details, location coordinates, citizen description,
    administrator instructions, and SLA targets for the assigned worker.
    """
    effective_id = worker_id or x_worker_id
    if not effective_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Worker ID is required.")

    tasks = WorkerService.get_assigned_tasks(db, effective_id)
    for t in tasks:
        if t.complaint_id == complaint_id:
            return t
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task for '{complaint_id}' not found for worker '{effective_id}'.")


@router.post("/tasks/{complaint_id}/accept")
def accept_task(
    complaint_id: str,
    req: WorkerAcceptRequest,
    db: Session = Depends(get_db)
):
    """
    Assigned worker accepts the task: transitions ASSIGNED -> ACCEPTED.
    """
    try:
        return WorkerService.accept_task(db, complaint_id, req.worker_id, req.notes)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/tasks/{complaint_id}/start")
def start_work(
    complaint_id: str,
    req: WorkerStartRequest,
    db: Session = Depends(get_db)
):
    """
    Worker commences inspection or physical work: transitions ACCEPTED -> IN_PROGRESS.
    """
    try:
        return WorkerService.start_work(db, complaint_id, req.worker_id, req.inspection_notes)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/tasks/{complaint_id}/unable-to-resolve")
def report_unable_to_resolve(
    complaint_id: str,
    req: WorkerUnableToResolveRequest,
    db: Session = Depends(get_db)
):
    """
    Worker reports an obstacle or inability to resolve: transitions to UNABLE_TO_RESOLVE.
    Requires an explanation of the blocker.
    """
    try:
        return WorkerService.report_unable_to_resolve(db, complaint_id, req.worker_id, req.reason)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/tasks/{complaint_id}/submit-resolution")
def submit_resolution(
    complaint_id: str,
    req: WorkerResolutionSubmitRequest,
    db: Session = Depends(get_db)
):
    """
    Worker submits completion details and after-photos.
    Moves complaint to VERIFICATION_REQUIRED for administrator inspection.
    Enforces that workers CANNOT mark work as COMPLETED directly.
    """
    try:
        return WorkerService.submit_resolution(db, complaint_id, req)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
