"""
gis_service.py
Geospatial and Sensitive-Site Proximity Service.
Implements server-side Haversine distance calculations, ward boundary resolution,
boundary dispute detection, and proximity risk estimation across sensitive facilities.
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class SensitiveFacility(BaseModel):
    id: str
    name: str
    facility_type: str  # "school", "hospital", "fire_station", "transit_hub", "substation", "residential"
    latitude: float
    longitude: float
    capacity: int = 500
    importance_weight: float = 1.0  # multiplier: schools=1.0, hospitals=1.0, transit=0.9


class WardBoundary(BaseModel):
    ward_id: str
    ward_name: str
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    primary_engineer_office: str
    dispute_buffer_meters: float = 50.0  # Buffer distance triggering cross-ward dispute


# Configurable municipal facilities in pilot zone (Amaravati / Vijayawada smart city grid)
DEFAULT_FACILITIES: List[SensitiveFacility] = [
    SensitiveFacility(
        id="FAC-SCH-01",
        name="St. Mary's Public School & Kindergarten",
        facility_type="school",
        latitude=16.5062,
        longitude=80.6480,
        capacity=850,
        importance_weight=1.0,
    ),
    SensitiveFacility(
        id="FAC-HOS-02",
        name="Apollo Emergency Hospital & Trauma Center",
        facility_type="hospital",
        latitude=16.5120,
        longitude=80.6520,
        capacity=450,
        importance_weight=1.0,
    ),
    SensitiveFacility(
        id="FAC-FIRE-03",
        name="City Central Fire & Disaster Rescue Station",
        facility_type="fire_station",
        latitude=16.5090,
        longitude=80.6440,
        capacity=60,
        importance_weight=0.95,
    ),
    SensitiveFacility(
        id="FAC-TRN-04",
        name="Central Metro & Inter-State Bus Terminal",
        facility_type="transit_hub",
        latitude=16.5150,
        longitude=80.6490,
        capacity=3500,
        importance_weight=0.90,
    ),
    SensitiveFacility(
        id="FAC-SUB-05",
        name="Grid Substation 33/11kV Ward 07",
        facility_type="substation",
        latitude=16.5040,
        longitude=80.6460,
        capacity=20,
        importance_weight=0.90,
    ),
]

# Configurable ward bounding boxes
DEFAULT_WARDS: List[WardBoundary] = [
    WardBoundary(
        ward_id="Ward 07",
        ward_name="Central Municipal Ward 07",
        min_lat=16.5000,
        max_lat=16.5100,
        min_lon=80.6400,
        max_lon=80.6500,
        primary_engineer_office="Executive Engineer Office, Sector 4",
    ),
    WardBoundary(
        ward_id="Ward 08",
        ward_name="North-East Municipal Ward 08",
        min_lat=16.5080,
        max_lat=16.5200,
        min_lon=80.6480,
        max_lon=80.6600,
        primary_engineer_office="Executive Engineer Office, Sector 5",
    ),
    WardBoundary(
        ward_id="Ward 09",
        ward_name="West Industrial Ward 09",
        min_lat=16.4950,
        max_lat=16.5050,
        min_lon=80.6300,
        max_lon=80.6420,
        primary_engineer_office="Industrial Drainage Division",
    ),
]


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes accurate geodesic surface distance between two WGS-84 points in meters.
    """
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


class ProximityEvaluationResult(BaseModel):
    normalized_s: float
    distance_meters: Optional[float]
    nearest_facility_id: Optional[str]
    nearest_facility_name: Optional[str]
    nearest_facility_type: Optional[str]
    proximity_status: str  # "confirmed_gis", "unknown_coordinates", "no_nearby_facility"
    confidence: float
    explanation: str


class WardRoutingResult(BaseModel):
    assigned_ward: str
    is_boundary_dispute: bool
    disputed_wards: List[str]
    jurisdiction_status: str  # "confirmed_single_ward", "disputed_boundary_zone", "unmapped_coordinates"
    responsible_office: str
    confidence: float
    explanation: str


class GISService:
    def __init__(
        self,
        facilities: Optional[List[SensitiveFacility]] = None,
        wards: Optional[List[WardBoundary]] = None
    ):
        self.facilities = facilities if facilities is not None else DEFAULT_FACILITIES
        self.wards = wards if wards is not None else DEFAULT_WARDS

    def validate_coordinates(self, lat: Optional[float], lon: Optional[float]) -> Tuple[bool, Optional[str]]:
        """
        Validates latitude and longitude ranges.
        """
        if lat is None or lon is None:
            return False, "Coordinates not provided."
        try:
            f_lat = float(lat)
            f_lon = float(lon)
        except (ValueError, TypeError):
            return False, "Coordinates must be valid numerical values."

        if not (-90.0 <= f_lat <= 90.0):
            return False, f"Latitude {f_lat} out of valid range [-90, +90]."
        if not (-180.0 <= f_lon <= 180.0):
            return False, f"Longitude {f_lon} out of valid range [-180, +180]."

        return True, None

    def calculate_sensitive_site_proximity(
        self,
        lat: Optional[float],
        lon: Optional[float]
    ) -> ProximityEvaluationResult:
        """
        Calculates distance to nearest sensitive facility and computes normalized S (0.0 to 1.0).
        Distance decay:
          <= 50m: 1.00 (High hazard threshold)
          50m - 150m: 0.85
          150m - 300m: 0.60
          300m - 500m: 0.35
          > 500m: 0.10
        If coordinates are missing/invalid, returns unknown proximity with conservative planning baseline.
        """
        is_valid, err = self.validate_coordinates(lat, lon)
        if not is_valid:
            return ProximityEvaluationResult(
                normalized_s=0.50,  # Conservative baseline for missing data
                distance_meters=None,
                nearest_facility_id=None,
                nearest_facility_name=None,
                nearest_facility_type=None,
                proximity_status="unknown_coordinates",
                confidence=0.30,
                explanation="No valid GPS coordinates provided; sensitive-site proximity is UNKNOWN. Conservative planning baseline (0.50) applied.",
            )

        if not self.facilities:
            return ProximityEvaluationResult(
                normalized_s=0.50,
                distance_meters=None,
                nearest_facility_id=None,
                nearest_facility_name=None,
                nearest_facility_type=None,
                proximity_status="unknown_coordinates",
                confidence=0.30,
                explanation="Municipal sensitive facilities catalog is unconfigured; proximity marked UNKNOWN.",
            )

        nearest_fac: Optional[SensitiveFacility] = None
        min_dist: float = float("inf")

        for fac in self.facilities:
            dist = haversine_distance_meters(lat, lon, fac.latitude, fac.longitude)
            if dist < min_dist:
                min_dist = dist
                nearest_fac = fac

        # Normalized scoring using distance bands
        if min_dist <= 50.0:
            norm_s = 1.0
        elif min_dist <= 150.0:
            norm_s = round(0.85 + (150.0 - min_dist) / 100.0 * 0.15, 2)
        elif min_dist <= 300.0:
            norm_s = round(0.60 + (300.0 - min_dist) / 150.0 * 0.25, 2)
        elif min_dist <= 500.0:
            norm_s = round(0.35 + (500.0 - min_dist) / 200.0 * 0.25, 2)
        else:
            norm_s = 0.10

        norm_s = min(1.0, max(0.0, norm_s * (nearest_fac.importance_weight if nearest_fac else 1.0)))

        return ProximityEvaluationResult(
            normalized_s=round(norm_s, 2),
            distance_meters=round(min_dist, 1),
            nearest_facility_id=nearest_fac.id if nearest_fac else None,
            nearest_facility_name=nearest_fac.name if nearest_fac else None,
            nearest_facility_type=nearest_fac.facility_type if nearest_fac else None,
            proximity_status="confirmed_gis",
            confidence=0.95,
            explanation=f"Nearest facility '{nearest_fac.name}' ({nearest_fac.facility_type}) is {min_dist:.1f}m away (Decay Proximity Score: {norm_s:.2f}).",
        )

    def resolve_ward_and_department(
        self,
        lat: Optional[float],
        lon: Optional[float],
        hazard_type: str = "general"
    ) -> WardRoutingResult:
        """
        Determines ward jurisdiction and flags boundary disputes if within 50m of overlapping borders.
        """
        is_valid, _ = self.validate_coordinates(lat, lon)
        if not is_valid:
            return WardRoutingResult(
                assigned_ward="Ward 07",  # Default central headquarters ward
                is_boundary_dispute=False,
                disputed_wards=[],
                jurisdiction_status="unmapped_coordinates",
                responsible_office="Central Municipal Emergency Operations Center",
                confidence=0.40,
                explanation="GPS coordinates unsupplied; assigned to Central Headquarters (Ward 07) pending verification.",
            )

        matching_wards: List[WardBoundary] = []
        dispute_wards: List[WardBoundary] = []

        for w in self.wards:
            # Check bounding box
            in_lat = w.min_lat <= lat <= w.max_lat
            in_lon = w.min_lon <= lon <= w.max_lon

            # Boundary proximity distance (approx 1 deg lat ~ 111km, 1 deg lon ~ 107km)
            dist_to_lat_min = abs(lat - w.min_lat) * 111000.0
            dist_to_lat_max = abs(lat - w.max_lat) * 111000.0
            dist_to_lon_min = abs(lon - w.min_lon) * 107000.0
            dist_to_lon_max = abs(lon - w.max_lon) * 107000.0
            min_border_dist = min(dist_to_lat_min, dist_to_lat_max, dist_to_lon_min, dist_to_lon_max)

            if in_lat and in_lon:
                matching_wards.append(w)
                if min_border_dist <= w.dispute_buffer_meters:
                    dispute_wards.append(w)
            elif min_border_dist <= w.dispute_buffer_meters:
                dispute_wards.append(w)

        if len(matching_wards) == 1 and not dispute_wards:
            w = matching_wards[0]
            return WardRoutingResult(
                assigned_ward=w.ward_id,
                is_boundary_dispute=False,
                disputed_wards=[],
                jurisdiction_status="confirmed_single_ward",
                responsible_office=w.primary_engineer_office,
                confidence=0.95,
                explanation=f"Coordinates definitively located within {w.ward_name}.",
            )

        # Boundary dispute detected (location is within 50m of ward border)
        all_involved = list({w.ward_id for w in (matching_wards + dispute_wards)})
        if len(all_involved) >= 2:
            primary_ward = matching_wards[0].ward_id if matching_wards else all_involved[0]
            return WardRoutingResult(
                assigned_ward=primary_ward,
                is_boundary_dispute=True,
                disputed_wards=all_involved,
                jurisdiction_status="disputed_boundary_zone",
                responsible_office="Joint Ward Boundary Triage Team (Auto-Escalated to Duty Officer)",
                confidence=0.60,
                explanation=f"LOCATION ON WARD BOUNDARY: Ambiguous border zone between {', '.join(all_involved)}. Flagged for authorized joint review; SLA clock active.",
            )

        if matching_wards:
            w = matching_wards[0]
            return WardRoutingResult(
                assigned_ward=w.ward_id,
                is_boundary_dispute=False,
                disputed_wards=[],
                jurisdiction_status="confirmed_single_ward",
                responsible_office=w.primary_engineer_office,
                confidence=0.90,
                explanation=f"Located within {w.ward_name}.",
            )

        # Fallback if coordinates fall just outside defined pilot ward polygons
        return WardRoutingResult(
            assigned_ward="Ward 07",
            is_boundary_dispute=False,
            disputed_wards=[],
            jurisdiction_status="unmapped_coordinates",
            responsible_office="Central Municipal Emergency Operations Center",
            confidence=0.50,
            explanation="Coordinates outside pilot ward polygons; routed to Central Operations.",
        )


# Global default GIS service instance
default_gis_service = GISService()
