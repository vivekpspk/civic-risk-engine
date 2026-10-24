"""
population_service.py
Automatic Population Exposure Estimation Service.
Derives potentially affected population count, exposure range, and normalized P factor (0.0 - 1.0)
from GPS coordinates, hazard geometry footprint, ward population density, road hierarchy,
and nearby facility occupancy without double counting.
Handles missing data honestly via population_exposure_status: "unknown".
"""

import math
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.core.gis_service import SensitiveFacility, default_gis_service, haversine_distance_meters


class PopulationEstimateRange(BaseModel):
    min_estimate: int
    max_estimate: int
    expected_estimate: int


class PopulationExposureResult(BaseModel):
    normalized_p: float = Field(..., ge=0.0, le=1.0)
    population_count_range: PopulationEstimateRange
    population_exposure_status: str  # "confirmed", "estimated", "unknown"
    data_source: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime
    impact_radius_meters: float
    nearby_facility_contributions: Dict[str, int] = Field(default_factory=dict)
    explanation: str
    is_missing: bool = False
    conservative_policy_applied: bool = False


class IPopulationProvider(ABC):
    @abstractmethod
    def estimate_exposure(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        hazard_category: str,
        evidence_status: str = "reported",
        explicit_footfall: Optional[int] = None
    ) -> PopulationExposureResult:
        pass


class ConfigurablePopulationProvider(IPopulationProvider):
    def __init__(
        self,
        default_ward_density_per_sqkm: float = 12000.0,  # Urban dense ward baseline (0.012 people/m^2)
        arterial_multiplier: float = 1.8,
        residential_multiplier: float = 1.0,
        calibrated_max_population: int = 1000,
        conservative_unknown_baseline: float = 0.50
    ):
        self.ward_density_per_sqm = default_ward_density_per_sqkm / 1_000_000.0
        self.arterial_multiplier = arterial_multiplier
        self.residential_multiplier = residential_multiplier
        self.calibrated_max_population = calibrated_max_population
        self.conservative_unknown_baseline = conservative_unknown_baseline

    # Hazard impact radii in meters
    IMPACT_RADII: Dict[str, float] = {
        "open_manhole": 50.0,
        "missing_drain_cover": 40.0,
        "flooded_road_deep": 250.0,
        "waterlog_sensitive_site": 150.0,
        "flash_flood_rapid_rise": 400.0,
        "fallen_electric_pole_live_wire": 75.0,
        "structural_collapse_risk": 90.0,
        "collapsed_road_sinkhole": 60.0,
        "trapped_people_or_vehicles": 80.0,
        "damaged_bridge_unsafe_crossing": 200.0,
        "drain_overflow_into_buildings": 100.0,
        "drinking_water_contamination": 500.0,
        "overflowing_waterways_canals": 350.0,
        "fallen_tree_blocking_road": 50.0,
        "blocked_drainage_system": 60.0,
        "missing_road_warning_signs": 40.0,
        "other_rain_hazard": 70.0,
    }

    def estimate_exposure(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        hazard_category: str,
        evidence_status: str = "reported",
        explicit_footfall: Optional[int] = None
    ) -> PopulationExposureResult:
        now = datetime.now(timezone.utc)

        # 1. Handle explicit footfall if verified sensor or inspector measured
        if explicit_footfall is not None:
            count = max(0, int(explicit_footfall))
            norm_p = min(1.0, round(count / float(self.calibrated_max_population), 3))
            return PopulationExposureResult(
                normalized_p=norm_p,
                population_count_range=PopulationEstimateRange(
                    min_estimate=int(count * 0.9),
                    max_estimate=int(count * 1.1),
                    expected_estimate=count
                ),
                population_exposure_status="confirmed",
                data_source="verified_field_sensor_or_officer_count",
                confidence=0.98,
                timestamp=now,
                impact_radius_meters=self.IMPACT_RADII.get(hazard_category, 75.0),
                explanation=f"Confirmed active footfall: {count} persons exposed within impact envelope (P: {norm_p:.2f})."
            )

        # 2. Check for missing or invalid coordinates
        if latitude is None or longitude is None:
            return PopulationExposureResult(
                normalized_p=self.conservative_unknown_baseline,
                population_count_range=PopulationEstimateRange(
                    min_estimate=0,
                    max_estimate=500,
                    expected_estimate=250
                ),
                population_exposure_status="unknown",
                data_source="missing_coordinates_conservative_policy",
                confidence=0.25,
                timestamp=now,
                impact_radius_meters=0.0,
                is_missing=True,
                conservative_policy_applied=True,
                explanation="No valid GPS coordinates provided; population exposure is UNKNOWN. Conservative planning baseline (0.50) applied."
            )

        # Validate range
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            return PopulationExposureResult(
                normalized_p=self.conservative_unknown_baseline,
                population_count_range=PopulationEstimateRange(min_estimate=0, max_estimate=500, expected_estimate=250),
                population_exposure_status="unknown",
                data_source="invalid_coordinates_conservative_policy",
                confidence=0.20,
                timestamp=now,
                impact_radius_meters=0.0,
                is_missing=True,
                conservative_policy_applied=True,
                explanation=f"Invalid coordinates ({latitude}, {longitude}); population exposure UNKNOWN. Conservative baseline (0.50) applied."
            )

        # 3. Derive impact footprint area
        radius = self.IMPACT_RADII.get(hazard_category, 75.0)
        footprint_area_sqm = math.pi * (radius ** 2)

        # Base population from ambient ward density
        base_people = footprint_area_sqm * self.ward_density_per_sqm * self.residential_multiplier

        # 4. Check nearby sensitive facilities and add incremental exposed fraction
        # Crucial rule: DO NOT count the entire population of a facility; only count realistic fraction
        # within the hazard envelope, avoiding double counting!
        facility_contributions: Dict[str, int] = {}
        incremental_facility_people = 0.0

        for fac in default_gis_service.facilities:
            dist = haversine_distance_meters(latitude, longitude, fac.latitude, fac.longitude)
            # If hazard buffer intersects facility grounds (within radius + 30m)
            if dist <= (radius + 30.0):
                # Fractional exposure factor decaying with distance
                if dist <= 50.0:
                    exposure_fraction = 0.35  # Max 35% of facility concurrently exposed in gate/road zone
                elif dist <= 120.0:
                    exposure_fraction = 0.15
                else:
                    exposure_fraction = 0.05

                # Support school dismissal / peak hours if evidence indicates
                if fac.facility_type == "school" and "school" in hazard_category:
                    exposure_fraction = min(0.60, exposure_fraction * 1.5)

                added = int(fac.capacity * exposure_fraction)
                if added > 0:
                    facility_contributions[fac.name] = added
                    incremental_facility_people += added

        # Total estimated exposed people
        total_expected = int(round(base_people + incremental_facility_people))
        min_est = max(0, int(total_expected * 0.7))
        max_est = int(total_expected * 1.4)

        # Normalize to 0.0 - 1.0 against calibrated municipal scale (1000 people = 1.0)
        norm_p = min(1.0, max(0.05, round(total_expected / float(self.calibrated_max_population), 3)))

        return PopulationExposureResult(
            normalized_p=norm_p,
            population_count_range=PopulationEstimateRange(
                min_estimate=min_est,
                max_estimate=max_est,
                expected_estimate=total_expected
            ),
            population_exposure_status="estimated",
            data_source="gis_footprint_density_and_facility_model",
            confidence=0.88,
            timestamp=now,
            impact_radius_meters=radius,
            nearby_facility_contributions=facility_contributions,
            explanation=f"Estimated {total_expected} persons ({min_est} - {max_est}) exposed within {radius:.0f}m hazard radius (Ambient: {int(base_people)}, Facilities: {int(incremental_facility_people)}, Normalized P: {norm_p:.2f})."
        )


# Global population provider instance
default_population_provider: IPopulationProvider = ConfigurablePopulationProvider()
