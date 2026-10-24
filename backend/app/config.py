"""
config.py
Configurable parameters, weights, priority bands, hazard mappings, and safety rules
for the Explainable Civic Risk Scoring and Priority Engine.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


def _load_env_file():
    for candidate in [
        Path(".env"),
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]:
        if candidate.is_file():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass


_load_env_file()


class GeminiConfig(BaseModel):
    api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    model_name: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"))
    fallback_models: List[str] = Field(
        default_factory=lambda: ["gemini-3.1-flash-lite", "gemini-3.6-flash", "gemini-3.5-flash"]
    )
    timeout_seconds: float = 12.0
    enabled: bool = True



class FactorWeights(BaseModel):
    hazard_severity: float = Field(0.25, ge=0.0, le=1.0, description="Weight for physical hazard severity (H)")
    sensitive_site_proximity: float = Field(0.20, ge=0.0, le=1.0, description="Weight for sensitive site proximity (S)")
    population_exposed: float = Field(0.20, ge=0.0, le=1.0, description="Weight for population exposed (P)")
    weather_risk: float = Field(0.15, ge=0.0, le=1.0, description="Weight for weather risk (W)")
    time_outstanding: float = Field(0.10, ge=0.0, le=1.0, description="Weight for time outstanding (T)")
    recurrence: float = Field(0.10, ge=0.0, le=1.0, description="Weight for historical recurrence (C)")

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "FactorWeights":
        total = (
            self.hazard_severity
            + self.sensitive_site_proximity
            + self.population_exposed
            + self.weather_risk
            + self.time_outstanding
            + self.recurrence
        )
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"Factor weights must sum to exactly 1.0. Current sum: {total:.4f}")
        return self


class PriorityBands(BaseModel):
    critical_min: float = Field(80.0, ge=0.0, le=100.0)
    high_min: float = Field(60.0, ge=0.0, le=100.0)
    medium_min: float = Field(35.0, ge=0.0, le=100.0)
    routine_min: float = Field(0.0, ge=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_bands_monotonic(self) -> "PriorityBands":
        if not (self.routine_min < self.medium_min < self.high_min < self.critical_min <= 100.0):
            raise ValueError("Priority bands must be strictly increasing: routine < medium < high < critical <= 100")
        return self


class SafetyRuleConfig(BaseModel):
    rule_id: str
    name: str
    condition_description: str
    hazard_types: List[str]
    min_proximity: Optional[float] = None
    min_weather_risk: Optional[float] = None
    min_population: Optional[float] = None
    required_evidence: List[str] = Field(default_factory=lambda: ["reported", "corroborated", "officially_verified"])
    trigger_result: str = "CRITICAL_REVIEW"
    severity_level: str = "Critical"
    explanation: str
    version: str = "1.0.0"


DEFAULT_SAFETY_RULES: List[SafetyRuleConfig] = [
    SafetyRuleConfig(
        rule_id="RULE-001",
        name="School/Sensitive Site Open Manhole Chamber",
        condition_description="Open manhole with proximity to sensitive site >= 0.70 and credible evidence.",
        hazard_types=["open_manhole"],
        min_proximity=0.70,
        required_evidence=["reported", "corroborated", "officially_verified"],
        trigger_result="CRITICAL_REVIEW",
        severity_level="Critical",
        explanation="Credible open manhole in high-proximity zone (<100m) of school or kindergarten triggers mandatory safety override for immediate dispatch.",
        version="1.0.0",
    ),
    SafetyRuleConfig(
        rule_id="RULE-002",
        name="Exposed Electrical Hazard in Flood/Rain Zone",
        condition_description="Exposed live electrical wires or transformer sparking with weather/flood risk >= 0.50.",
        hazard_types=["exposed_electrical_hazard", "fallen_electric_pole_live_wire", "water_entering_electrical_substation"],
        min_weather_risk=0.50,
        required_evidence=["reported", "corroborated", "officially_verified"],
        trigger_result="CRITICAL_REVIEW",
        severity_level="Critical",
        explanation="Exposed electrical hazard in wet conditions poses catastrophic electrocution risk; immediate emergency review triggered.",
        version="1.0.0",
    ),
    SafetyRuleConfig(
        rule_id="RULE-003",
        name="Blocked Hospital/Emergency Route Access",
        condition_description="Severe flooding, collapsed structure, or debris obstructing hospital emergency ambulance ingress/egress.",
        hazard_types=["blocked_hospital_access", "severe_flooding"],
        min_proximity=0.80,
        required_evidence=["reported", "corroborated", "officially_verified"],
        trigger_result="CRITICAL_REVIEW",
        severity_level="Critical",
        explanation="Obstruction of primary arterial access to healthcare facilities triggers immediate priority override.",
        version="1.0.0",
    ),
    SafetyRuleConfig(
        rule_id="RULE-004",
        name="Severe Flash Flood Inundation in Densely Populated Zone",
        condition_description="Rapid water accumulation with population exposure >= 0.80.",
        hazard_types=["severe_flooding", "flash_flood_rapid_rise"],
        min_population=0.80,
        required_evidence=["corroborated", "officially_verified"],
        trigger_result="CRITICAL_REVIEW",
        severity_level="Critical",
        explanation="High-depth flash flooding with high population exposure poses mass stranding or drowning threat.",
        version="1.0.0",
    ),
    SafetyRuleConfig(
        rule_id="RULE-005",
        name="People or Vehicles Trapped by Floodwater",
        condition_description="Reports of individuals, school children, or passengers marooned or trapped in rising floodwaters.",
        hazard_types=["trapped_people_or_vehicles"],
        required_evidence=["reported", "corroborated", "officially_verified"],
        trigger_result="CRITICAL_REVIEW",
        severity_level="Critical",
        explanation="Direct human life safety distress call; immediate search and rescue dispatch required regardless of missing data inputs.",
        version="1.0.0",
    ),
    SafetyRuleConfig(
        rule_id="RULE-006",
        name="Imminent Structural Collapse or Damaged Bridge",
        condition_description="Cracking compound walls, dilapidated building collapse threat, or bridge washout during storm.",
        hazard_types=["structural_collapse_risk", "damaged_bridge_unsafe_crossing", "collapsed_road_sinkhole"],
        required_evidence=["reported", "corroborated", "officially_verified"],
        trigger_result="CRITICAL_REVIEW",
        severity_level="Critical",
        explanation="Catastrophic infrastructure failure threat; mandatory cordon and road closure protocol activated.",
        version="1.0.0",
    ),
]

DEFAULT_HAZARD_SEVERITY_MAP: Dict[str, float] = {
    # 24 Heavy Rain Taxonomy Categories
    "open_manhole": 1.0,
    "missing_drain_cover": 0.85,
    "flooded_road_deep": 0.90,
    "waterlog_sensitive_site": 0.85,
    "flash_flood_rapid_rise": 0.95,
    "overflowing_stormwater_drain": 0.75,
    "blocked_drainage_system": 0.60,
    "drain_overflow_into_buildings": 0.85,
    "sewer_overflow_contaminated": 0.80,
    "collapsed_road_sinkhole": 0.90,
    "damaged_bridge_unsafe_crossing": 0.95,
    "landslide_mudslide_rockfall": 0.90,
    "fallen_tree_blocking_road": 0.55,
    "fallen_electric_pole_live_wire": 1.0,
    "water_entering_electrical_substation": 0.95,
    "structural_collapse_risk": 0.95,
    "flooding_near_healthcare_facility": 0.90,
    "flooding_affecting_evacuation_routes": 0.85,
    "drinking_water_contamination": 0.85,
    "overflowing_waterways_canals": 0.85,
    "trapped_people_or_vehicles": 1.0,
    "missing_road_warning_signs": 0.45,
    "dangerous_construction_excavation": 0.85,
    "other_rain_hazard": 0.50,
    # Backward compatibility aliases
    "exposed_electrical_hazard": 1.0,
    "blocked_hospital_access": 1.0,
    "severe_flooding": 0.90,
    "shallow_waterlogging": 0.40,
    "pothole": 0.30,
    "garbage_dump": 0.25,
    "street_light_outage": 0.20,
    "curb_erosion": 0.15,
}


class RiskModelConfig(BaseModel):
    version: str = "v1.0.0"
    formula: str = "Risk Score = 100 * (0.25H + 0.20S + 0.20P + 0.15W + 0.10T + 0.10C)"
    status: str = "prototype_unvalidated"
    label: str = "Configurable, unvalidated prototype thresholds requiring empirical municipal validation"
    weights: FactorWeights = Field(default_factory=FactorWeights)
    priority_bands: PriorityBands = Field(default_factory=PriorityBands)
    hazard_severity_map: Dict[str, float] = Field(default_factory=lambda: DEFAULT_HAZARD_SEVERITY_MAP.copy())
    safety_rules: List[SafetyRuleConfig] = Field(default_factory=lambda: DEFAULT_SAFETY_RULES.copy())
    time_escalation_cap_hours: float = 24.0
    recurrence_window_days: float = 30.0
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)


# Global active configuration instance
active_config = RiskModelConfig()
