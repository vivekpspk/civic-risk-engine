"""
test_risk_engine.py
Comprehensive automated test suite verifying all 14 acceptance criteria
for the Civic Risk Scoring and Priority Engine.
"""

import os
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import FactorWeights, PriorityBands, RiskModelConfig, active_config
from app.core.risk_scorer import FactorInputs, compute_risk_score
from app.core.feature_extractor import (
    extract_hazard_severity, extract_sensitive_site_proximity,
    extract_population_exposed, extract_weather_risk,
    extract_time_outstanding, extract_recurrence
)
from app.core.safety_rules import evaluate_safety_rules
from app.core.priority_engine import (
    evaluate_sla_status, rank_priority_queue
)
from app.models.database import Base, get_db, IncidentModel, AssessmentModel
from app.models.schemas import CreateIncidentRequest, FactorInputsSchema, AssessIncidentRequest
from app.services.incident_service import IncidentService
from app.services.simulation_service import SimulationService
from app.main import app

# In-memory SQLite with StaticPool so all threads/sessions share the same in-memory DB
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =============================================================================
# TEST 1: Correct Weighted Score Calculation (Exact Sample Match: 74.0/100)
# =============================================================================
def test_01_correct_weighted_score_calculation():
    """
    Given: H=1.0, S=0.9, P=0.7, W=0.8, T=0.2, C=0.3
    Formula: 100 * (0.25*1.0 + 0.20*0.9 + 0.20*0.7 + 0.15*0.8 + 0.10*0.2 + 0.10*0.3)
    Expected: 100 * (0.25 + 0.18 + 0.14 + 0.12 + 0.02 + 0.03) = 74.0 / 100
    """
    factors = FactorInputs(
        hazard_severity=1.0,
        sensitive_site_proximity=0.9,
        population_exposed=0.7,
        weather_risk=0.8,
        time_outstanding=0.2,
        recurrence=0.3
    )
    result = compute_risk_score(factors)
    assert result.rounded_score == 74.0
    assert result.factor_contributions["hazard_severity"] == 25.0
    assert result.factor_contributions["sensitive_site_proximity"] == 18.0
    assert result.factor_contributions["population_exposed"] == 14.0
    assert result.factor_contributions["weather_risk"] == 12.0
    assert result.factor_contributions["time_outstanding"] == 2.0
    assert result.factor_contributions["recurrence"] == 3.0
    assert result.priority_band == "High"


# =============================================================================
# TEST 2: Invalid Factor Values Outside 0–1
# =============================================================================
def test_02_invalid_factor_values_outside_range():
    # Value > 1.0 should fail
    with pytest.raises(Exception):
        FactorInputs(
            hazard_severity=1.5,
            sensitive_site_proximity=0.5,
            population_exposed=0.5,
            weather_risk=0.5,
            time_outstanding=0.5,
            recurrence=0.5
        )

    # Value < 0.0 should fail
    with pytest.raises(Exception):
        FactorInputs(
            hazard_severity=-0.2,
            sensitive_site_proximity=0.5,
            population_exposed=0.5,
            weather_risk=0.5,
            time_outstanding=0.5,
            recurrence=0.5
        )


# =============================================================================
# TEST 3: Weight Validation (Sum Must Equal 1.0)
# =============================================================================
def test_03_weight_validation():
    # Valid sum
    w_valid = FactorWeights(
        hazard_severity=0.25, sensitive_site_proximity=0.20, population_exposed=0.20,
        weather_risk=0.15, time_outstanding=0.10, recurrence=0.10
    )
    assert round(w_valid.hazard_severity + w_valid.sensitive_site_proximity + w_valid.population_exposed +
                 w_valid.weather_risk + w_valid.time_outstanding + w_valid.recurrence, 2) == 1.0

    # Invalid sum (< 1.0)
    with pytest.raises(ValueError, match="Factor weights must sum to exactly 1.0"):
        FactorWeights(
            hazard_severity=0.20, sensitive_site_proximity=0.20, population_exposed=0.20,
            weather_risk=0.15, time_outstanding=0.10, recurrence=0.10
        )

    # Invalid sum (> 1.0)
    with pytest.raises(ValueError, match="Factor weights must sum to exactly 1.0"):
        FactorWeights(
            hazard_severity=0.35, sensitive_site_proximity=0.20, population_exposed=0.20,
            weather_risk=0.15, time_outstanding=0.10, recurrence=0.10
        )


# =============================================================================
# TEST 4: Correct Priority-Band Boundaries
# =============================================================================
def test_04_priority_band_boundaries():
    # Critical: >= 80.0
    f_crit = FactorInputs(hazard_severity=0.9, sensitive_site_proximity=0.9, population_exposed=0.9,
                          weather_risk=0.9, time_outstanding=0.5, recurrence=0.5)
    assert compute_risk_score(f_crit).priority_band == "Critical"

    # High: 60.0 to 79.99
    f_high = FactorInputs(hazard_severity=1.0, sensitive_site_proximity=0.9, population_exposed=0.7,
                          weather_risk=0.8, time_outstanding=0.2, recurrence=0.3)
    assert compute_risk_score(f_high).priority_band == "High"

    # Medium: 35.0 to 59.99
    f_med = FactorInputs(hazard_severity=0.5, sensitive_site_proximity=0.4, population_exposed=0.4,
                         weather_risk=0.4, time_outstanding=0.3, recurrence=0.2)
    assert compute_risk_score(f_med).priority_band == "Medium"

    # Routine: < 35.0
    f_rout = FactorInputs(hazard_severity=0.2, sensitive_site_proximity=0.1, population_exposed=0.1,
                          weather_risk=0.2, time_outstanding=0.1, recurrence=0.1)
    assert compute_risk_score(f_rout).priority_band == "Routine"


# =============================================================================
# TEST 5: Safety Override Independent of Weighted Score
# =============================================================================
def test_05_safety_override_independent_of_weighted_score():
    # An open manhole with proximity >= 0.70 triggers RULE-001 (Critical Review)
    # even if other factors are tiny resulting in low physical score!
    factors = {
        "hazard_severity": 0.3,
        "sensitive_site_proximity": 0.85,
        "population_exposed": 0.1,
        "weather_risk": 0.1,
        "time_outstanding": 0.0,
        "recurrence": 0.0
    }
    f_obj = FactorInputs(**factors)
    score_res = compute_risk_score(f_obj)
    # Physical score is low (approx 26.5 - Routine)
    assert score_res.priority_band == "Routine"

    # But Safety Rule RULE-001 triggers Critical Review!
    safety_res = evaluate_safety_rules("open_manhole", factors, evidence_status="corroborated")
    assert safety_res.active is True
    assert safety_res.effective_severity == "Critical"
    assert any(r.rule_id == "RULE-001" for r in safety_res.triggered_rules)


# =============================================================================
# TEST 6: Missing and Stale Data Handling
# =============================================================================
def test_06_missing_and_stale_data_handling():
    # 1. Missing population exposed vs Zero population exposed
    zero_pop_det, zero_warn = extract_population_exposed(population_count=0)
    assert zero_pop_det.value == 0.0
    assert zero_pop_det.is_missing is False
    assert zero_warn is None

    missing_pop_det, miss_warn = extract_population_exposed(population_count=None)
    assert missing_pop_det.value == 0.5  # conservative planning default
    assert missing_pop_det.is_missing is True
    assert miss_warn is not None
    assert "missing" in miss_warn.lower()

    # 2. Stale weather data
    stale_w_det, stale_warn = extract_weather_risk(explicit_value=0.7, stale=True)
    assert stale_w_det.uncertainty_status == "stale_data"
    assert stale_warn is not None
    assert "stale" in stale_warn.lower()


# =============================================================================
# TEST 7: Dynamic Time-Factor Calculation
# =============================================================================
def test_07_dynamic_time_factor_calculation():
    base_t = datetime(2026, 10, 24, 0, 0, 0, tzinfo=timezone.utc)
    # 6 hours elapsed out of 24h cap -> 0.25
    t_6h = base_t + timedelta(hours=6)
    det_6h = extract_time_outstanding(base_t, current_time=t_6h)
    assert det_6h.value == 0.25

    # 24 hours elapsed -> 1.00
    t_24h = base_t + timedelta(hours=24)
    det_24h = extract_time_outstanding(base_t, current_time=t_24h)
    assert det_24h.value == 1.00

    # 48 hours elapsed -> capped at 1.00
    t_48h = base_t + timedelta(hours=48)
    det_48h = extract_time_outstanding(base_t, current_time=t_48h)
    assert det_48h.value == 1.00


# =============================================================================
# TEST 8: Duplicate Reports Not Inflating Recurrence
# =============================================================================
def test_08_duplicate_reports_not_inflating_recurrence():
    # When is_duplicate_in_same_cluster is True, warning is flagged and count doesn't increase
    det, warn = extract_recurrence(distinct_incident_count=1, is_duplicate_in_same_cluster=True)
    assert det.value == 0.2  # 1 distinct incident = 0.20
    assert warn is not None
    assert "did not inflate recurrence" in warn


# =============================================================================
# TEST 9: SLA Breach Detection
# =============================================================================
def test_09_sla_breach_detection():
    now = datetime(2026, 10, 24, 6, 0, 0, tzinfo=timezone.utc)
    created = now - timedelta(hours=3)

    # 1. Within SLA (deadline 2 hours in future)
    sla_future = now + timedelta(hours=2)
    res_within = evaluate_sla_status(created, sla_future, current_time=now)
    assert res_within.sla_status == "within_sla"
    assert res_within.is_breached is False

    # 2. SLA Breached (deadline 30 minutes in the past)
    sla_past = now - timedelta(minutes=30)
    res_breached = evaluate_sla_status(created, sla_past, current_time=now)
    assert res_breached.sla_status == "breached"
    assert res_breached.is_breached is True
    assert "SLA BREACHED" in res_breached.escalation_alert


# =============================================================================
# TEST 10: Deterministic Ranking and Tie-Breaking
# =============================================================================
def test_10_deterministic_ranking_and_tie_breaking(db_session):
    now = datetime(2026, 10, 24, 8, 0, 0, tzinfo=timezone.utc)

    # Incident 1: Critical Safety Override
    inc1 = CreateIncidentRequest(
        incident_id="INC-T1-OVERRIDE",
        hazard_type="open_manhole",
        created_at=now - timedelta(hours=1),
        factors=FactorInputsSchema(hazard_severity=0.5, sensitive_site_proximity=0.9, population_exposed=0.5,
                                   weather_risk=0.5, time_outstanding=0.1, recurrence=0.1)
    )
    IncidentService.create_incident(db_session, inc1)

    # Incident 2: High score (82.0) without override
    inc2 = CreateIncidentRequest(
        incident_id="INC-T2-HIGH-SCORE",
        hazard_type="shallow_waterlogging",
        created_at=now - timedelta(hours=2),
        factors=FactorInputsSchema(hazard_severity=0.8, sensitive_site_proximity=0.5, population_exposed=0.9,
                                   weather_risk=0.9, time_outstanding=0.8, recurrence=0.8)
    )
    IncidentService.create_incident(db_session, inc2)

    # Incident 3: Identical score to Incident 4, but older
    inc3 = CreateIncidentRequest(
        incident_id="INC-T3-OLDER",
        hazard_type="pothole",
        created_at=now - timedelta(hours=5),
        factors=FactorInputsSchema(hazard_severity=0.3, sensitive_site_proximity=0.2, population_exposed=0.3,
                                   weather_risk=0.3, time_outstanding=0.1, recurrence=0.1)
    )
    IncidentService.create_incident(db_session, inc3)

    # Incident 4: Identical score to Incident 3, but newer
    inc4 = CreateIncidentRequest(
        incident_id="INC-T4-NEWER",
        hazard_type="pothole",
        created_at=now - timedelta(hours=1),
        factors=FactorInputsSchema(hazard_severity=0.3, sensitive_site_proximity=0.2, population_exposed=0.3,
                                   weather_risk=0.3, time_outstanding=0.1, recurrence=0.1)
    )
    IncidentService.create_incident(db_session, inc4)

    queue = IncidentService.get_priority_queue(db_session)
    assert len(queue) == 4

    # 1st must be the active override
    assert queue[0].incident_id == "INC-T1-OVERRIDE"
    # 2nd must be the high physical risk score
    assert queue[1].incident_id == "INC-T2-HIGH-SCORE"
    # 3rd must be the older incident (tie-breaker)
    assert queue[2].incident_id == "INC-T3-OLDER"
    # 4th must be the newer incident
    assert queue[3].incident_id == "INC-T4-NEWER"


# =============================================================================
# TEST 11: Audit-History Persistence (Never Overwrites)
# =============================================================================
def test_11_audit_history_persistence(db_session):
    inc_req = CreateIncidentRequest(
        incident_id="INC-AUDIT-TEST",
        hazard_type="pothole",
        factors=FactorInputsSchema(hazard_severity=0.3, sensitive_site_proximity=0.2, population_exposed=0.2,
                                   weather_risk=0.2, time_outstanding=0.1, recurrence=0.1)
    )
    IncidentService.create_incident(db_session, inc_req)

    # Assess multiple times with varying weather
    for w in [0.3, 0.6, 0.9]:
        IncidentService.assess_incident(
            db_session,
            "INC-AUDIT-TEST",
            AssessIncidentRequest(factors=FactorInputsSchema(
                hazard_severity=0.3, sensitive_site_proximity=0.2, population_exposed=0.2,
                weather_risk=w, time_outstanding=0.2, recurrence=0.1
            ))
        )

    detail = IncidentService.get_incident_detail(db_session, "INC-AUDIT-TEST")
    # Initial assessment + 3 re-assessments = 4 assessments persisted
    assert len(detail.assessment_history) == 4
    # Check that previous assessments were not overwritten
    scores = [a.risk_score for a in detail.assessment_history]
    assert len(set(scores)) > 1  # distinct scores stored


# =============================================================================
# TEST 12: Exactly 140 Reports in the Simulator
# =============================================================================
def test_12_exactly_140_reports_in_simulator(db_session):
    sim_res = SimulationService.run_140_reports_simulation(db_session)
    assert sim_res["total_reports_ingested"] == 140
    assert sim_res["report_allocations"]["school_manhole_reports"] == 28
    assert sim_res["report_allocations"]["boundary_waterlogging_reports"] == 36
    assert sim_res["report_allocations"]["coordinated_bot_attack_reports"] == 31
    assert sim_res["report_allocations"]["genuine_emergency_in_attack_zone"] == 1
    assert sim_res["report_allocations"]["routine_civic_issues_reports"] == 44
    assert sim_res["report_allocations"]["total_verified"] == 140


# =============================================================================
# TEST 13: Genuine Hazard Preserved Under Coordinated Abuse Attack
# =============================================================================
def test_13_genuine_hazard_preserved_under_coordinated_abuse(db_session):
    sim_res = SimulationService.run_140_reports_simulation(db_session)
    assert sim_res["genuine_hazard_preserved_under_attack"] is True

    # Check queue directly: INC-304-GENUINE-ELECTRICAL must be ranked in Top 2
    queue = IncidentService.get_priority_queue(db_session)
    top_ids = [it.incident_id for it in queue[:2]]
    assert "INC-304-GENUINE-ELECTRICAL" in top_ids

    # Meanwhile, the spam attack (INC-303-SUSPICIOUS-SPAM) is quarantined and ranked lower
    spam_item = next(it for it in queue if it.incident_id == "INC-303-SUSPICIOUS-SPAM")
    genuine_item = next(it for it in queue if it.incident_id == "INC-304-GENUINE-ELECTRICAL")
    assert genuine_item.queue_rank < spam_item.queue_rank


# =============================================================================
# TEST 14: API Validation and Error Handling
# =============================================================================
def test_14_api_validation_and_error_handling(client):
    # 1. Health check returns 200
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    # 2. 404 for non-existent incident
    res_404 = client.get("/incidents/NON_EXISTENT_999/risk")
    assert res_404.status_code == 404

    # 3. 422 for factor out of bounds in creation
    bad_payload = {
        "incident_id": "INC-BAD-FACTOR",
        "hazard_type": "open_manhole",
        "factors": {
            "hazard_severity": 2.5,  # Invalid: > 1.0
            "sensitive_site_proximity": 0.5,
            "population_exposed": 0.5,
            "weather_risk": 0.5,
            "time_outstanding": 0.5,
            "recurrence": 0.5
        }
    }
    res_422 = client.post("/incidents", json=bad_payload)
    assert res_422.status_code == 422

    # 4. 403 for unauthorized override role
    client.post("/incidents", json={
        "incident_id": "INC-OVERRIDE-TEST",
        "hazard_type": "open_manhole",
        "factors": {
            "hazard_severity": 0.5, "sensitive_site_proximity": 0.5, "population_exposed": 0.5,
            "weather_risk": 0.5, "time_outstanding": 0.5, "recurrence": 0.5
        }
    })
    res_403 = client.post("/incidents/INC-OVERRIDE-TEST/override", json={
        "authorized_by": "John Doe",
        "role": "unauthorized_citizen",
        "reason": "I want faster service",
        "target_severity": "Critical"
    })
    assert res_403.status_code == 403
