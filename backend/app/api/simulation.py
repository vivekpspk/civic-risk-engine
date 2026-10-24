"""
simulation.py
FastAPI router for generating and running the 140-report Challenge 10 stress test.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.simulation_service import SimulationService

router = APIRouter(prefix="/simulation", tags=["140-Report Scenario Simulator"])

_last_simulation_cache: Dict[str, Any] = {}


@router.post("/run-140-reports")
def run_simulation(db: Session = Depends(get_db)):
    """
    Executes the 140-report replayable scenario simulation:
    - 28 School open manhole reports
    - 36 Boundary waterlogging reports
    - 32 Coordinated false reports (with 1 genuine emergency preserved)
    - 44 Routine civic reports
    Total = Exactly 140.
    """
    global _last_simulation_cache
    result = SimulationService.run_140_reports_simulation(db)
    _last_simulation_cache = result
    return result


@router.get("/status")
def get_simulation_status(db: Session = Depends(get_db)):
    """
    Returns the latest simulation results and cluster statistics.
    """
    global _last_simulation_cache
    if not _last_simulation_cache:
        # Run automatically if cache is empty
        _last_simulation_cache = SimulationService.run_140_reports_simulation(db)
    return _last_simulation_cache
