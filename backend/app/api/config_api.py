"""
config_api.py
FastAPI router for inspecting and updating the Risk Model configuration,
weights, priority bands, and safety rules.
"""

from fastapi import APIRouter, HTTPException, status
from app.config import RiskModelConfig, FactorWeights, PriorityBands, active_config
from app.models.schemas import UpdateRiskModelConfigRequest

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.get("/risk-model", response_model=RiskModelConfig)
def get_risk_model_config():
    """
    Returns the active risk model configuration, factor weights,
    priority bands, and configured safety rules.
    """
    return active_config


@router.post("/risk-model", response_model=RiskModelConfig)
def update_risk_model_config(req: UpdateRiskModelConfigRequest):
    """
    Updates the active risk model configuration with validation and role authorization.
    Requires role authorization (admin or municipal_commissioner).
    Validates that weights sum to exactly 1.0.
    """
    authorized_roles = ["admin", "municipal_commissioner", "supervisor"]
    if req.role.lower() not in authorized_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{req.role}' is not authorized to update core risk model parameters. Required: {authorized_roles}"
        )

    try:
        if req.weights:
            new_weights = FactorWeights(**req.weights)
            active_config.weights = new_weights

        if req.priority_bands:
            new_bands = PriorityBands(**req.priority_bands)
            active_config.priority_bands = new_bands

        if req.time_escalation_cap_hours is not None:
            active_config.time_escalation_cap_hours = max(1.0, float(req.time_escalation_cap_hours))

        return active_config
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
