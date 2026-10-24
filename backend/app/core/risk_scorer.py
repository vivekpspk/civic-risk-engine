"""
risk_scorer.py
Deterministic 6-factor civic risk scoring calculation, factor contribution explanations,
priority banding, and rounding rules.
"""

from typing import Dict, List, Tuple
from pydantic import BaseModel, Field, field_validator


class FactorInputs(BaseModel):
    hazard_severity: float = Field(..., ge=0.0, le=1.0, description="H: Physical hazard severity [0.0, 1.0]")
    sensitive_site_proximity: float = Field(..., ge=0.0, le=1.0, description="S: Sensitive site proximity [0.0, 1.0]")
    population_exposed: float = Field(..., ge=0.0, le=1.0, description="P: Population density/footfall exposed [0.0, 1.0]")
    weather_risk: float = Field(..., ge=0.0, le=1.0, description="W: Weather/flash-flood risk index [0.0, 1.0]")
    time_outstanding: float = Field(..., ge=0.0, le=1.0, description="T: Time elapsed normalized [0.0, 1.0]")
    recurrence: float = Field(..., ge=0.0, le=1.0, description="C: Historical failure recurrence [0.0, 1.0]")

    @field_validator("*")
    @classmethod
    def check_range(cls, v: float, info) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"Factor '{info.field_name}' must be within [0.0, 1.0]. Given: {v}")
        return v


class RiskCalculationResult(BaseModel):
    raw_score: float
    rounded_score: float
    formula_version: str
    factor_contributions: Dict[str, float]
    priority_band: str
    explanations: List[str]
    disclaimer: str = "This score reflects comparative operational urgency, not the physical probability of an accident."


def compute_risk_score(factors: FactorInputs, config=None) -> RiskCalculationResult:
    """
    Computes deterministic risk score according to:
    Risk Score = 100 * (0.25H + 0.20S + 0.20P + 0.15W + 0.10T + 0.10C)
    """
    from app.config import active_config
    cfg = config or active_config
    weights = cfg.weights
    bands = cfg.priority_bands

    # Individual contributions
    h_contrib = 100.0 * weights.hazard_severity * factors.hazard_severity
    s_contrib = 100.0 * weights.sensitive_site_proximity * factors.sensitive_site_proximity
    p_contrib = 100.0 * weights.population_exposed * factors.population_exposed
    w_contrib = 100.0 * weights.weather_risk * factors.weather_risk
    t_contrib = 100.0 * weights.time_outstanding * factors.time_outstanding
    c_contrib = 100.0 * weights.recurrence * factors.recurrence

    raw_score = h_contrib + s_contrib + p_contrib + w_contrib + t_contrib + c_contrib
    rounded_score = round(raw_score, 1)

    contributions = {
        "hazard_severity": round(h_contrib, 1),
        "sensitive_site_proximity": round(s_contrib, 1),
        "population_exposed": round(p_contrib, 1),
        "weather_risk": round(w_contrib, 1),
        "time_outstanding": round(t_contrib, 1),
        "recurrence": round(c_contrib, 1),
    }

    # Priority banding
    if rounded_score >= bands.critical_min:
        priority_band = "Critical"
    elif rounded_score >= bands.high_min:
        priority_band = "High"
    elif rounded_score >= bands.medium_min:
        priority_band = "Medium"
    else:
        priority_band = "Routine"

    explanations = [
        f"Hazard severity contributes {contributions['hazard_severity']} points.",
        f"Sensitive-site proximity contributes {contributions['sensitive_site_proximity']} points.",
        f"Population exposure contributes {contributions['population_exposed']} points.",
        f"Weather risk contributes {contributions['weather_risk']} points.",
        f"Time outstanding contributes {contributions['time_outstanding']} points.",
        f"Historical recurrence contributes {contributions['recurrence']} points.",
    ]

    return RiskCalculationResult(
        raw_score=raw_score,
        rounded_score=rounded_score,
        formula_version=cfg.version,
        factor_contributions=contributions,
        priority_band=priority_band,
        explanations=explanations,
    )
