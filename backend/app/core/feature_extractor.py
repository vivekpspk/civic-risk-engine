"""
feature_extractor.py
Feature extraction and normalization module for the 6 civic risk factors.
Extracts Hazard Severity, Sensitive-Site Proximity, Population Exposure,
Weather Risk, Time Outstanding, and Recurrence with source attribution and uncertainty tracking.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class FactorDetail(BaseModel):
    name: str
    value: float = Field(..., ge=0.0, le=1.0)
    source: str  # e.g., "configured_hazard_mapping", "gis_distance_decay", "manual_input", "sensor_weather_feed"
    timestamp: Optional[datetime] = None
    is_missing: bool = False
    uncertainty_status: str = "confirmed"  # "confirmed", "missing_defaulted", "stale_data", "unverified_estimate"
    explanation: str


class ExtractedFeatures(BaseModel):
    factors: Dict[str, FactorDetail]
    normalized_values: Dict[str, float]
    uncertainty_warnings: List[str]


def extract_hazard_severity(
    hazard_type: str,
    explicit_value: Optional[float] = None,
    config=None
) -> FactorDetail:
    from app.config import active_config
    cfg = config or active_config

    if explicit_value is not None:
        val = max(0.0, min(1.0, float(explicit_value)))
        return FactorDetail(
            name="hazard_severity",
            value=val,
            source="explicit_user_input",
            uncertainty_status="confirmed",
            explanation=f"Explicit hazard severity provided: {val:.2f}"
        )

    clean_type = hazard_type.lower().strip().replace(" ", "_")
    if clean_type in cfg.hazard_severity_map:
        val = cfg.hazard_severity_map[clean_type]
        return FactorDetail(
            name="hazard_severity",
            value=val,
            source="configured_hazard_mapping",
            uncertainty_status="confirmed",
            explanation=f"Severity mapped from catalog for '{hazard_type}': {val:.2f}"
        )

    # Unknown hazard type fallback
    return FactorDetail(
        name="hazard_severity",
        value=0.5,
        source="default_unknown_mapping",
        is_missing=True,
        uncertainty_status="unverified_estimate",
        explanation=f"Unknown hazard category '{hazard_type}'; defaulted to conservative baseline 0.50."
    )


def extract_sensitive_site_proximity(
    distance_meters: Optional[float] = None,
    explicit_value: Optional[float] = None,
    site_type: Optional[str] = None
) -> FactorDetail:
    if explicit_value is not None:
        val = max(0.0, min(1.0, float(explicit_value)))
        return FactorDetail(
            name="sensitive_site_proximity",
            value=val,
            source="explicit_user_input",
            uncertainty_status="confirmed",
            explanation=f"Explicit sensitive-site proximity provided: {val:.2f}"
        )

    if distance_meters is not None:
        d = max(0.0, float(distance_meters))
        # Documented distance decay: 0-50m = 1.0, 50-500m linear decay to 0.0
        if d <= 50.0:
            val = 1.0
        elif d >= 500.0:
            val = 0.0
        else:
            val = round(1.0 - ((d - 50.0) / 450.0), 3)

        desc = f"Site '{site_type or 'sensitive location'}' is {d:.1f}m away (Decay Proximity: {val:.2f})"
        return FactorDetail(
            name="sensitive_site_proximity",
            value=val,
            source="gis_distance_decay",
            uncertainty_status="confirmed",
            explanation=desc
        )

    # Missing proximity
    return FactorDetail(
        name="sensitive_site_proximity",
        value=0.2,
        source="unspecified_default",
        is_missing=True,
        uncertainty_status="missing_defaulted",
        explanation="No GIS coordinates or sensitive-site distance supplied; assumed low-exposure residential baseline 0.20."
    )


def extract_population_exposed(
    population_count: Optional[int] = None,
    explicit_value: Optional[float] = None,
    density_category: Optional[str] = None
) -> Tuple[FactorDetail, Optional[str]]:
    """
    Carefully keeps missing population distinct from zero population.
    """
    warning = None
    if explicit_value is not None:
        val = max(0.0, min(1.0, float(explicit_value)))
        return FactorDetail(
            name="population_exposed",
            value=val,
            source="explicit_user_input",
            uncertainty_status="confirmed",
            explanation=f"Explicit population exposure index provided: {val:.2f}"
        ), None

    if population_count is not None:
        # Zero population is a valid, distinct measurement
        if population_count == 0:
            return FactorDetail(
                name="population_exposed",
                value=0.0,
                source="measured_census_zero",
                uncertainty_status="confirmed",
                explanation="Confirmed zero active footfall/exposure in perimeter."
            ), None
        # Normalized mapping up to 1000 people
        val = min(1.0, round(population_count / 1000.0, 3))
        return FactorDetail(
            name="population_exposed",
            value=val,
            source="measured_footfall_count",
            uncertainty_status="confirmed",
            explanation=f"Estimated {population_count} exposed individuals in impact radius (Normalized: {val:.2f})."
        ), None

    # Missing population data: distinct from zero!
    warning = "Population exposure data is missing; defaulted to conservative planning baseline 0.50 (NOT confirmed zero)."
    return FactorDetail(
        name="population_exposed",
        value=0.5,
        source="missing_data_default",
        is_missing=True,
        uncertainty_status="missing_defaulted",
        explanation="Missing census/footfall sensor data. Defaulted to conservative 0.50."
    ), warning


def extract_weather_risk(
    precipitation_mm_hr: Optional[float] = None,
    explicit_value: Optional[float] = None,
    stale: bool = False
) -> Tuple[FactorDetail, Optional[str]]:
    warning = None
    if explicit_value is not None:
        val = max(0.0, min(1.0, float(explicit_value)))
        status = "stale_data" if stale else "confirmed"
        if stale:
            warning = "Weather telemetry feed is stale (>60 mins old); risk factor may be under- or over-estimated."
        return FactorDetail(
            name="weather_risk",
            value=val,
            source="explicit_user_input",
            uncertainty_status=status,
            explanation=f"Explicit weather risk provided: {val:.2f} ({status})"
        ), warning

    if precipitation_mm_hr is not None:
        p = max(0.0, float(precipitation_mm_hr))
        # 0 mm = 0.0, 100 mm/hr = 1.0
        val = min(1.0, round(p / 100.0, 3))
        status = "stale_data" if stale else "confirmed"
        if stale:
            warning = "Weather sensor telemetry is stale (>60 mins old)."
        return FactorDetail(
            name="weather_risk",
            value=val,
            source="meteorological_sensor",
            uncertainty_status=status,
            explanation=f"Precipitation of {p:.1f} mm/hr maps to weather risk {val:.2f}."
        ), warning

    warning = "Live weather telemetry unavailable; weather factor set to regional baseline 0.50."
    return FactorDetail(
        name="weather_risk",
        value=0.5,
        source="weather_feed_missing",
        is_missing=True,
        uncertainty_status="missing_defaulted",
        explanation="Weather data feed unavailable; defaulted to regional convective storm baseline 0.50."
    ), warning


def extract_time_outstanding(
    created_at: datetime,
    current_time: Optional[datetime] = None,
    explicit_value: Optional[float] = None,
    config=None
) -> FactorDetail:
    if explicit_value is not None:
        val = max(0.0, min(1.0, float(explicit_value)))
        return FactorDetail(
            name="time_outstanding",
            value=val,
            source="explicit_user_input",
            uncertainty_status="confirmed",
            explanation=f"Explicit time outstanding provided: {val:.2f}"
        )

    from app.config import active_config
    cfg = config or active_config
    now = current_time or datetime.now(timezone.utc)
    
    # Ensure timezone awareness
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    elapsed_seconds = max(0.0, (now - created_at).total_seconds())
    elapsed_hours = elapsed_seconds / 3600.0
    cap_hours = cfg.time_escalation_cap_hours or 24.0

    # Linear escalation capped at 1.0 at cap_hours
    val = min(1.0, round(elapsed_hours / cap_hours, 3))
    return FactorDetail(
        name="time_outstanding",
        value=val,
        source="timestamp_escalation_function",
        timestamp=created_at,
        uncertainty_status="confirmed",
        explanation=f"Incident active for {elapsed_hours:.1f} hours (Capped at {cap_hours:.0f}h: {val:.2f})."
    )


def extract_recurrence(
    distinct_incident_count: Optional[int] = None,
    explicit_value: Optional[float] = None,
    is_duplicate_in_same_cluster: bool = False
) -> Tuple[FactorDetail, Optional[str]]:
    """
    Calculates recurrence using distinct related incidents.
    Duplicate reports belonging to the same incident cluster must NOT inflate recurrence!
    """
    warning = None
    if explicit_value is not None:
        val = max(0.0, min(1.0, float(explicit_value)))
        return FactorDetail(
            name="recurrence",
            value=val,
            source="explicit_user_input",
            uncertainty_status="confirmed",
            explanation=f"Explicit recurrence index provided: {val:.2f}"
        ), None

    if is_duplicate_in_same_cluster:
        warning = "Multiple citizen submissions belong to the same incident cluster; duplicate count did not inflate recurrence."

    count = max(0, distinct_incident_count or 0)
    # 0 previous incidents = 0.0, 5+ previous distinct incidents = 1.0
    val = min(1.0, round(count / 5.0, 2))
    return FactorDetail(
        name="recurrence",
        value=val,
        source="distinct_historical_incident_index",
        uncertainty_status="confirmed",
        explanation=f"{count} distinct historical incidents recorded at asset/location in past 30 days (Recurrence: {val:.2f})."
    ), warning
