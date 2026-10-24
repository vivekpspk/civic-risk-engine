"""
verify_e2e.py
End-to-end integration verification script testing the live application.
"""

import sys
import os

backend_path = r"C:\Users\vivek\.gemini\antigravity\scratch\impactx-overclock\civic_risk_engine\backend"
sys.path.insert(0, backend_path)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("1. Testing Health Endpoint...")
res_health = client.get('/health')
assert res_health.status_code == 200
print("   Health:", res_health.json())

print("2. Testing Section 8 Exact Sample...")
sample_payload = {
    'incident_id': 'INC-001',
    'hazard_type': 'open_manhole',
    'created_at': '2026-10-24T04:00:00Z',
    'factors': {
        'hazard_severity': 1.0,
        'sensitive_site_proximity': 0.9,
        'population_exposed': 0.7,
        'weather_risk': 0.8,
        'time_outstanding': 0.2,
        'recurrence': 0.3
    },
    'evidence_status': 'corroborated',
    'sla_deadline': '2026-10-24T06:00:00Z'
}
res_inc = client.post('/incidents', json=sample_payload)
if res_inc.status_code == 409:
    res_inc = client.post('/incidents/INC-001/assess', json={'factors': sample_payload['factors']})
assert res_inc.status_code in [200, 201]
data = res_inc.json()
print("   Incident ID:", data['incident_id'])
print("   Calculated Risk Score:", data['risk_score'])
print("   Priority Band:", data['priority_band'])
print("   Factor Contributions:", data['factor_contributions'])
assert data['risk_score'] == 74.0, f"Expected 74.0, got {data['risk_score']}"
assert data['factor_contributions']['hazard_severity'] == 25.0
assert data['factor_contributions']['sensitive_site_proximity'] == 18.0
assert data['factor_contributions']['population_exposed'] == 14.0
assert data['factor_contributions']['weather_risk'] == 12.0
assert data['factor_contributions']['time_outstanding'] == 2.0
assert data['factor_contributions']['recurrence'] == 3.0
print("   => EXACT SAMPLE TEST MATCH VERIFIED: 74.0/100!")

print("3. Testing Priority Queue...")
res_q = client.get('/priority-queue')
assert res_q.status_code == 200
print("   Active Queue Length:", len(res_q.json()))

print("4. Testing 140-Report Simulation...")
res_sim = client.post('/simulation/run-140-reports')
assert res_sim.status_code == 200
sim_data = res_sim.json()
print("   Total Reports Ingested:", sim_data['total_reports_ingested'])
assert sim_data['total_reports_ingested'] == 140
print("   Allocations:", sim_data['report_allocations'])
assert sim_data['report_allocations']['school_manhole_reports'] == 28
assert sim_data['report_allocations']['boundary_waterlogging_reports'] == 36
assert sim_data['report_allocations']['coordinated_bot_attack_reports'] == 31
assert sim_data['report_allocations']['genuine_emergency_in_attack_zone'] == 1
assert sim_data['report_allocations']['routine_civic_issues_reports'] == 44
print("   Proposed Clusters Count:", sim_data['proposed_clusters_count'])
print("   Genuine Hazard Preserved:", sim_data['genuine_hazard_preserved_under_attack'])
assert sim_data['genuine_hazard_preserved_under_attack'] is True

print("5. Testing Manual Authorized Override...")
res_ov = client.post('/incidents/INC-101-SCHOOL-MANHOLE/override', json={
    'authorized_by': 'Commissioner R. Sharma',
    'role': 'municipal_commissioner',
    'reason': 'Emergency protocol activation for child safety.',
    'target_severity': 'Critical'
})
assert res_ov.status_code == 200
ov_data = res_ov.json()
assert ov_data['safety_override']['active'] is True
print("   Override successfully recorded and applied:", ov_data['safety_override']['summary'])

print("6. Testing Static Frontend Mount...")
res_fe = client.get('/')
assert res_fe.status_code == 200
assert 'text/html' in res_fe.headers['content-type']
print("   Frontend HTML served successfully!")

print("7. Testing Gemini AI Automated Analysis & Triage...")
res_ai = client.post('/api/ai/analyze', json={
    'description': 'Water is accumulating rapidly near a school, and an uncovered manhole is visible during heavy rain.',
    'location': 'Ward 07 School Gate',
    'category_hint': 'open_manhole'
})
assert res_ai.status_code == 200
ai_data = res_ai.json()
print("   Gemini Model:", ai_data['ai_model_used'])
print("   Detected Hazard:", ai_data['detected_hazard_type'])
print("   Severity:", ai_data['hazard_severity'])
print("   Emergency Override:", ai_data['emergency_safety_override'])
print("   Reasoning:", ai_data['ai_reasoning_summary'])
assert ai_data['detected_hazard_type'] in ['open_manhole', 'waterlog_sensitive_site']
assert ai_data['emergency_safety_override'] is True
assert len(ai_data['ai_reasoning_summary']) > 15
print("   => GEMINI AI CIVIC TRIAGE VERIFIED SUCCESSFULLY!")

print("\nALL END-TO-END VERIFICATION CHECKS PASSED PERFECTLY!")
