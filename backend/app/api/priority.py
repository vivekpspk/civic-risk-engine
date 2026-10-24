"""
priority.py
FastAPI router for the Dynamic Priority Queue.
"""

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.core.priority_engine import PriorityQueueItem
from app.services.incident_service import IncidentService

router = APIRouter(tags=["Priority Queue"])


@router.get("/priority-queue", response_model=List[PriorityQueueItem])
def get_priority_queue(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Returns the active municipal priority queue ranked deterministically:
    1. Active Safety Overrides (Critical emergency review first)
    2. Physical Risk Score (Highest to lowest)
    3. SLA Urgency (Breached > Imminent > Within SLA)
    4. Incident Age (Older incidents first as tie-breaker)
    """
    return IncidentService.get_priority_queue(db, limit=limit)
