"""
test_complaint_engine.py
Comprehensive automated test suite covering all 22 mandatory criteria from Section 13
of the IMPACTX 2026 Challenge 10 Master Prompt.
Verifies end-to-end citizen complaint intake, automatic risk calculation,
24 rain hazard taxonomy classification, GIS proximity, population exposure estimation,
boundary dispute detection, safety overrides, SLA separation, and privacy protection.
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base, get_db, IncidentModel, AssessmentModel
from app.models.schemas import CitizenComplaintCreate, AdminStatusUpdate, AdminAssignmentUpdate, ManualOverrideRequest
from app.core.hazard_taxonomy import RAIN_HAZARD_TAXONOMY, classify_hazard_from_text
from app.core.gis_service import default_gis_service, haversine_distance_meters
from app.core.population_service import default_population_provider
from app.core.weather_service import default_weather_provider
from app.services.complaint_service import ComplaintService
from app.services.evidence_service import strip_image_metadata_and_sanitize, redact_sensitive_text
from app.main import app

# Shared In-memory database with StaticPool for isolated tests
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 1: Normal waterlogging complaint is accepted and assessed automatically
# ---------------------------------------------------------------------------
def test_01_normal_waterlogging_complaint_accepted_and_assessed(client):
    payload = {
        "description": "Shallow water accumulating on the side of the road after rain.",
        "latitude": 16.5020,
        "longitude": 80.6420,
        "location_address": "4th Cross Road, Ward 07",
        "consent_given": True,
    }
    res = client.post("/api/complaints", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["complaint_id"].startswith("CMP-2026-")
    assert data["status"] == "submitted"
    assert data["risk_score"] > 0.0
    assert data["priority_band"] in ["Routine", "Medium", "High", "Critical"]
    assert "roadway" in data["plain_language_explanation"].lower() or "water" in data["plain_language_explanation"].lower()
    assert data["assigned_department"] != "Unassigned"


# ---------------------------------------------------------------------------
# Test 2: Uncovered manhole during heavy rain receives justified elevated priority
# ---------------------------------------------------------------------------
def test_02_uncovered_manhole_receives_elevated_priority(client):
    payload = {
        "description": "An uncovered manhole is visible during heavy rain near a school gate.",
        "latitude": 16.5063,  # ~15m from St. Mary's School (16.5062, 80.6480)
        "longitude": 80.6481,
        "consent_given": True,
    }
    res = client.post("/api/complaints", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["hazard_category"] == "open_manhole"
    assert data["safety_override_active"] is True
    assert data["priority_band"] == "Critical"
    assert "school" in data["plain_language_explanation"].lower()


# ---------------------------------------------------------------------------
# Test 3: Credible electrical hazard near floodwater triggers urgent review
# ---------------------------------------------------------------------------
def test_03_electrical_hazard_in_floodwater_triggers_urgent_review(client):
    payload = {
        "description": "Live electric wire has snapped and fallen into standing floodwater with sparking.",
        "latitude": 16.5050,
        "longitude": 80.6450,
        "consent_given": True,
    }
    res = client.post("/api/complaints", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["hazard_category"] == "fallen_electric_pole_live_wire"
    assert data["safety_override_active"] is True
    assert data["priority_band"] == "Critical"
    assert "RULE-002" in data["plain_language_explanation"] or "SAFETY OVERRIDE" in data["plain_language_explanation"]


# ---------------------------------------------------------------------------
# Test 4: Report about people trapped in floodwater triggers urgent review
# ---------------------------------------------------------------------------
def test_04_people_trapped_in_floodwater_triggers_urgent_review(client):
    payload = {
        "description": "Two senior citizens and a child are trapped inside a car stuck in deep rising floodwater.",
        "latitude": 16.5030,
        "longitude": 80.6410,
        "consent_given": True,
    }
    res = client.post("/api/complaints", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["hazard_category"] == "trapped_people_or_vehicles"
    assert data["priority_band"] == "Critical"
    assert data["safety_override_active"] is True
    assert "immediate" in data["estimated_response_window"].lower()


# ---------------------------------------------------------------------------
# Test 5: GPS proximity is calculated correctly for a configured facility
# ---------------------------------------------------------------------------
def test_05_gps_proximity_calculated_correctly_for_facility():
    # St Mary's school is at (16.5062, 80.6480)
    # Point ~30m away
    dist = haversine_distance_meters(16.5062, 80.6480, 16.5064, 80.6481)
    assert dist < 50.0

    prox = default_gis_service.calculate_sensitive_site_proximity(16.5064, 80.6481)
    assert prox.proximity_status == "confirmed_gis"
    assert prox.distance_meters is not None
    assert prox.distance_meters < 50.0
    assert prox.normalized_s == 1.0  # Under 50m gets maximum proximity score 1.0


# ---------------------------------------------------------------------------
# Test 6: Missing GPS is handled safely
# ---------------------------------------------------------------------------
def test_06_missing_gps_handled_safely(client):
    payload = {
        "description": "Waterlogging observed on Main Bazaar road, no GPS available.",
        "latitude": None,
        "longitude": None,
        "location_address": "Main Bazaar Road",
    }
    res = client.post("/api/complaints", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["complaint_id"].startswith("CMP-2026-")
    assert data["risk_score"] > 0.0
    # Proximity is marked as unknown with conservative baseline
    assert "conservative planning baseline" in data["plain_language_explanation"].lower() or "unknown" in data["plain_language_explanation"].lower()


# ---------------------------------------------------------------------------
# Test 7: Missing weather data is identified instead of fabricated
# ---------------------------------------------------------------------------
def test_07_missing_weather_data_identified_honestly():
    # When coordinates are None and ward is None, weather service returns fallback
    w = default_weather_provider.get_weather_risk(None, None, ward=None)
    assert w.weather_status == "unavailable_fallback"
    assert w.is_missing is True
    assert "unconfigured" in w.explanation.lower() or "conservative" in w.explanation.lower()


# ---------------------------------------------------------------------------
# Test 8: Unknown population exposure is not silently treated as zero
# ---------------------------------------------------------------------------
def test_08_unknown_population_exposure_not_silently_zero():
    pop = default_population_provider.estimate_exposure(
        latitude=None,
        longitude=None,
        hazard_category="open_manhole"
    )
    assert pop.population_exposure_status == "unknown"
    assert pop.is_missing is True
    assert pop.conservative_policy_applied is True
    # Crucial check: Normalized P must NOT be 0.0!
    assert pop.normalized_p == 0.50
    assert "conservative planning baseline" in pop.explanation.lower()


# ---------------------------------------------------------------------------
# Test 9: Time outstanding updates as a complaint ages
# ---------------------------------------------------------------------------
def test_09_time_outstanding_updates_as_complaint_ages(db_session):
    past_time = datetime.now(timezone.utc) - timedelta(hours=12)
    inc = IncidentModel(
        incident_id="CMP-TEST-TIME",
        hazard_type="flooded_road_deep",
        ward="Ward 07",
        created_at=past_time,
        status="submitted",
    )
    db_session.add(inc)
    db_session.commit()

    # Reassess via IncidentService
    from app.services.incident_service import IncidentService
    assessment = IncidentService.assess_incident(db_session, "CMP-TEST-TIME")
    assert assessment.factor_contributions["time_outstanding"] > 0.0
    # 12 hours out of 24h cap should yield ~0.50 factor (10% weight -> ~5.0 pts)
    assert assessment.factor_contributions["time_outstanding"] >= 4.0


# ---------------------------------------------------------------------------
# Test 10: Duplicate reports do not artificially inflate recurrence
# ---------------------------------------------------------------------------
def test_10_duplicate_reports_do_not_inflate_recurrence(client):
    # Submit first report
    p1 = {"description": "Pothole on 2nd Avenue", "latitude": 16.501, "longitude": 80.641, "category_hint": "pothole"}
    r1 = client.post("/api/complaints", json=p1).json()

    # Submit exact same report (duplicate submission by same/another user)
    p2 = {"description": "Pothole on 2nd Avenue", "latitude": 16.501, "longitude": 80.641, "category_hint": "pothole"}
    r2 = client.post("/api/complaints", json=p2).json()

    # Verify recurrence factor is not inflated by immediate duplicate reports
    assert abs(r1["risk_score"] - r2["risk_score"]) <= 5.0
    # Also verify exact recurrence parity
    if "factor_contributions" in r1 and "factor_contributions" in r2 and r1["factor_contributions"] and r2["factor_contributions"]:
        assert r1["factor_contributions"]["recurrence"] == r2["factor_contributions"]["recurrence"]


# ---------------------------------------------------------------------------
# Test 11: Multiple independent reports can contribute corroboration appropriately
# ---------------------------------------------------------------------------
def test_11_multiple_independent_reports_corroborate(db_session):
    from app.services.simulation_service import SimulationService
    res = SimulationService.run_140_reports_simulation(db_session)
    assert res["total_reports_ingested"] == 140
    # School cluster had 28 independent reports merged into verified cluster
    assert res["report_allocations"]["school_manhole_reports"] == 28
    assert res["proposed_clusters_count"] > 0


# ---------------------------------------------------------------------------
# Test 12: Ward-boundary ambiguity is flagged
# ---------------------------------------------------------------------------
def test_12_ward_boundary_ambiguity_flagged(client):
    # Coordinate exactly on border between Ward 07 and Ward 08 (lat 16.5085, lon 80.6485)
    payload = {
        "description": "Heavy waterlogging on the border road between Sector 4 and Sector 5.",
        "latitude": 16.5085,
        "longitude": 80.6485,
    }
    res = client.post("/api/complaints", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["is_boundary_dispute"] is True
    assert len(data["disputed_wards"]) >= 2
    assert "disputed_boundary_zone" in data["plain_language_explanation"] or "WARD BOUNDARY" in data["plain_language_explanation"]


# ---------------------------------------------------------------------------
# Test 13: Routine complaint does not outrank credible imminent danger merely due to volume
# ---------------------------------------------------------------------------
def test_13_routine_complaints_do_not_outrank_imminent_danger(client):
    # 1. Critical dangerous incident
    danger_payload = {
        "description": "Uncovered sewer manhole right in front of school bus stop during heavy storm.",
        "latitude": 16.5062,
        "longitude": 80.6480,
    }
    danger_res = client.post("/api/complaints", json=danger_payload).json()

    # 2. Routine complaint with volume hint
    routine_payload = {
        "description": "Missing street sign and minor leaves on sidewalk.",
        "latitude": 16.5010,
        "longitude": 80.6410,
    }
    routine_res = client.post("/api/complaints", json=routine_payload).json()

    assert danger_res["priority_band"] == "Critical"
    assert routine_res["priority_band"] in ["Routine", "Medium"]
    assert danger_res["risk_score"] > routine_res["risk_score"]

    # Verify priority queue order
    queue_res = client.get("/api/admin/priority-queue").json()
    ranks = {item["incident_id"]: item["queue_rank"] for item in queue_res}
    assert ranks[danger_res["complaint_id"]] < ranks[routine_res["complaint_id"]]


# ---------------------------------------------------------------------------
# Test 14: Authorized manual override records administrator and reason
# ---------------------------------------------------------------------------
def test_14_authorized_manual_override_records_admin_and_reason(client):
    # Submit complaint
    c_res = client.post("/api/complaints", json={"description": "Moderate water ponding on street.", "latitude": 16.502, "longitude": 80.642}).json()
    cid = c_res["complaint_id"]

    override_payload = {
        "authorized_by": "Commissioner R. Sharma",
        "role": "municipal_commissioner",
        "reason": "VIP convoy and emergency school dismissal route.",
        "target_severity": "Critical",
    }
    res = client.post(f"/api/admin/complaints/{cid}/override", json=override_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["priority_band"] == "Critical"
    assert data["safety_override"]["active"] is True
    assert "Commissioner R. Sharma" in data["safety_override"]["summary"]


# ---------------------------------------------------------------------------
# Test 15: Unauthorized user cannot apply override
# ---------------------------------------------------------------------------
def test_15_unauthorized_user_cannot_apply_override(client):
    c_res = client.post("/api/complaints", json={"description": "Moderate water on street."}).json()
    cid = c_res["complaint_id"]

    invalid_payload = {
        "authorized_by": "Random Citizen",
        "role": "citizen_guest",  # Invalid unauthorized role
        "reason": "I want faster service",
        "target_severity": "Critical",
    }
    res = client.post(f"/api/admin/complaints/{cid}/override", json=invalid_payload)
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Test 16: SLA escalation works independently of physical risk scoring
# ---------------------------------------------------------------------------
def test_16_sla_escalation_independent_of_physical_risk(db_session, client):
    # Routine physical risk (pothole), but SLA deadline 5 hours in the past
    past_sla = datetime.now(timezone.utc) - timedelta(hours=5)
    inc = IncidentModel(
        incident_id="CMP-SLA-BREACH",
        hazard_type="pothole",
        ward="Ward 07",
        created_at=datetime.now(timezone.utc) - timedelta(hours=30),
        sla_deadline=past_sla,
        status="submitted",
    )
    db_session.add(inc)
    db_session.commit()

    from app.services.incident_service import IncidentService
    IncidentService.assess_incident(db_session, "CMP-SLA-BREACH")

    queue = client.get("/api/admin/priority-queue").json()
    item = next(i for i in queue if i["incident_id"] == "CMP-SLA-BREACH")
    assert item["is_sla_breached"] is True
    assert item["sla_status"] == "breached"
    # Physical score is low-to-moderate, but SLA is strictly breached
    assert item["risk_score"] < 50.0


# ---------------------------------------------------------------------------
# Test 17: Public endpoints do not expose private contact information
# ---------------------------------------------------------------------------
def test_17_public_endpoints_do_not_expose_private_contact(client):
    payload = {
        "description": "Water logging near my shop. Call me at 9876543210 if needed.",
        "latitude": 16.502,
        "longitude": 80.642,
        "reporter_name": "John Doe",
        "reporter_phone": "+91-9876543210",
        "reporter_email": "john.doe@example.com",
    }
    res = client.post("/api/complaints", json=payload)
    assert res.status_code == 201
    data = res.json()

    # Public response check
    assert "reporter_name" not in data
    assert "reporter_phone" not in data
    assert "reporter_email" not in data
    assert "9876543210" not in data["plain_language_explanation"]

    # Public GET status check
    cid = data["complaint_id"]
    get_res = client.get(f"/api/complaints/{cid}").json()
    assert "reporter_phone" not in get_res
    assert "reporter_email" not in get_res


# ---------------------------------------------------------------------------
# Test 18: Image metadata is stripped and redaction operates safely
# ---------------------------------------------------------------------------
def test_18_image_metadata_stripped_and_redaction():
    # Test text redaction
    sample_text = "Car with plate AP 09 AB 1234 hit a drain. Call 987-654-3210 or email test@city.gov."
    clean, was_redacted = redact_sensitive_text(sample_text)
    assert was_redacted is True
    assert "[PHONE_REDACTED]" in clean
    assert "[VEHICLE_PLATE_REDACTED]" in clean
    assert "[EMAIL_REDACTED]" in clean

    # Test binary metadata scrub
    dummy_bytes = b"\xff\xd8\xff\xe1\x00\x18Exif\x00\x00GPSLatitude12345"
    sanitized_bytes, stripped = strip_image_metadata_and_sanitize(dummy_bytes, "test.jpg")
    assert stripped is True
    assert b"GPSLatitude" not in sanitized_bytes


# ---------------------------------------------------------------------------
# Test 19: Invalid coordinates and malformed requests are rejected
# ---------------------------------------------------------------------------
def test_19_invalid_coordinates_rejected(client):
    # Latitude out of bounds (95.0 > 90.0)
    payload = {
        "description": "Invalid latitude report",
        "latitude": 95.0,
        "longitude": 80.0,
    }
    res = client.post("/api/complaints", json=payload)
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Test 20: Administrator queue reflects the latest saved assessments
# ---------------------------------------------------------------------------
def test_20_admin_queue_reflects_latest_saved_assessments(client):
    res = client.post("/api/complaints", json={"description": "Collapsed road sinkhole with deep crater.", "latitude": 16.502, "longitude": 80.642}).json()
    cid = res["complaint_id"]

    queue = client.get("/api/admin/priority-queue").json()
    assert any(i["incident_id"] == cid for i in queue)


# ---------------------------------------------------------------------------
# Test 21: Complaint submission works when optional location or weather integrations are unavailable
# ---------------------------------------------------------------------------
def test_21_submission_works_without_optional_integrations(client):
    payload = {
        "description": "Tree fallen on the street blocking traffic during rain.",
        # No latitude, longitude, address, or weather sensor specified
    }
    res = client.post("/api/complaints", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["hazard_category"] == "fallen_tree_blocking_road"
    assert data["risk_score"] > 0.0


# ---------------------------------------------------------------------------
# Test 22: Every assessment includes useful explanation and traceable factor sources
# ---------------------------------------------------------------------------
def test_22_traceable_factor_sources_and_explanations(client):
    res = client.post("/api/complaints", json={
        "description": "Flash flooding rising quickly in residential street.",
        "latitude": 16.504,
        "longitude": 80.646
    }).json()
    cid = res["complaint_id"]

    risk_res = client.get(f"/api/complaints/{cid}/risk").json()
    assert "hazard_severity" in risk_res["factor_contributions"]
    assert "sensitive_site_proximity" in risk_res["factor_contributions"]
    assert "population_exposed" in risk_res["factor_contributions"]
    assert "weather_risk" in risk_res["factor_contributions"]
    assert len(risk_res["explanation"]) >= 3
    assert risk_res["recommended_action"] != ""
