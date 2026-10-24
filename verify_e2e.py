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

print("\n8. Testing Complete Citizen-to-Worker-to-Admin-to-Citizen Complaint Lifecycle Scenario...")
# Step 1: Citizen submits complaint with before photo
print("   Step 1: Citizen submits uncovered manhole complaint with before-photo...")
sub_resp = client.post('/api/complaints', json={
    'description': 'Water is accumulating near a school, and an uncovered manhole is visible during heavy rain.',
    'latitude': 16.5063,
    'longitude': 80.6481,
    'location_address': 'School Main Gate, Ward 07',
    'reporter_name': 'Anil Rao',
    'reporter_phone': '+91-9876543210',
    'consent_sms': True,
    'evidence_photos': ['data:image/jpeg;base64,' + 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=']
})
assert sub_resp.status_code == 201
comp_data = sub_resp.json()
demo_cid = comp_data['complaint_id']
print(f"      Generated Complaint ID: {demo_cid}")
print(f"      Initial Priority: {comp_data['priority_band']} (Risk Score: {comp_data['risk_score']})")
print(f"      Assigned Department: {comp_data['assigned_department']}")
assert demo_cid.startswith("CIV-2026-")

# Step 2: Administrator inspects priority queue & assigns worker
print("   Step 2: Administrator assigns municipal field worker WRK-101...")
assign_resp = client.post(f'/api/admin/complaints/{demo_cid}/assign', json={
    'worker_id': 'WRK-101',
    'admin_id': 'COMMISSIONER-SHARMA',
    'instructions': 'Immediate dispatch: replace damaged lid with ductile iron cover and secure perimeter.'
})
assert assign_resp.status_code == 200
print(f"      Assigned Status: {assign_resp.json()['status']}")
assert assign_resp.json()['status'] == 'ASSIGNED'

# Step 3: Worker accepts assignment and starts work
print("   Step 3: Worker WRK-101 accepts task and arrives on-site...")
acc_resp = client.post(f'/api/worker/tasks/{demo_cid}/accept', json={'worker_id': 'WRK-101'})
assert acc_resp.status_code == 200
start_resp = client.post(f'/api/worker/tasks/{demo_cid}/start', json={
    'worker_id': 'WRK-101',
    'inspection_notes': 'Arrived on-site. Roadwater 4 inches deep. Cordoning off manhole.'
})
assert start_resp.status_code == 200
print(f"      Worker Progress Status: {start_resp.json()['status']}")
assert start_resp.json()['status'] == 'IN_PROGRESS'

# Step 4: Worker uploads after-resolution photo and submits completion
print("   Step 4: Worker uploads after-photo and submits resolution report...")
import io
dummy_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
f_upload = client.post(
    f'/api/worker/complaints/{demo_cid}/evidence/after',
    files={'file': ('after_repair.jpg', io.BytesIO(dummy_jpeg), 'image/jpeg')},
    data={'worker_id': 'WRK-101', 'caption': 'New heavy duty sealed manhole cover installed.'}
)
assert f_upload.status_code == 201
after_ev_id = f_upload.json()['evidence_id']

sub_res_resp = client.post(f'/api/worker/tasks/{demo_cid}/submit-resolution', json={
    'worker_id': 'WRK-101',
    'description': 'Installed heavy-duty reinforced ductile iron cover with locking pins.',
    'action_taken': 'Manhole sealed and tested under water accumulation. Hazard eliminated.',
    'after_evidence_ids': [after_ev_id]
})
assert sub_res_resp.status_code == 200
print(f"      Resolution Submitted Status: {sub_res_resp.json()['status']} (Verification: {sub_res_resp.json()['verification_status']})")
assert sub_res_resp.json()['status'] == 'VERIFICATION_REQUIRED'

# Step 5: Administrator compares side-by-side evidence & approves resolution
print("   Step 5: Administrator compares before-and-after evidence and approves resolution...")
comp_resp = client.get(f'/api/complaints/{demo_cid}/comparison')
assert comp_resp.status_code == 200
comp_dossier = comp_resp.json()
print(f"      Before Photos Count: {comp_dossier['total_before_count']}, After Photos Count: {comp_dossier['total_after_count']}")
assert comp_dossier['total_before_count'] >= 1
assert comp_dossier['total_after_count'] >= 1

verify_resp = client.post(f'/api/admin/complaints/{demo_cid}/verify-resolution', json={
    'decision': 'approve',
    'admin_id': 'COMMISSIONER-SHARMA',
    'notes': 'Verified before and after photographic evidence. Work approved as fully resolved.'
})
assert verify_resp.status_code == 200
print(f"      Verified Status: {verify_resp.json()['status']}")
assert verify_resp.json()['status'] == 'COMPLETED'

# Step 6: Citizen inspects public tracking dossier
print("   Step 6: Citizen verifies resolution through public tracking portal...")
pub_track = client.get(f'/api/public/complaints/{demo_cid}')
assert pub_track.status_code == 200
track_data = pub_track.json()
print(f"      Public Status: {track_data['status']}")
print(f"      Resolution Description: {track_data['resolution_description']}")
print(f"      Action Performed: {track_data['action_performed']}")
print(f"      Status Timeline Stages: {len(track_data['status_timeline'])}")
assert track_data['status'] == 'COMPLETED'
assert len(track_data['before_photos']) >= 1
assert len(track_data['after_photos']) >= 1
# Verify zero leaks of citizen contact
track_str = str(track_data)
assert '+91-9876543210' not in track_str
assert 'Anil Rao' not in track_str

# Step 7: Notification dispatch verification
print("   Step 7: Verifying citizen completion SMS notification status...")
notif_resp = client.get('/api/admin/notifications')
assert notif_resp.status_code == 200
notifications = notif_resp.json()
matching_notif = next((n for n in notifications if n['complaint_id'] == demo_cid), None)
assert matching_notif is not None
print(f"      SMS Provider: {matching_notif['provider']}")
print(f"      Delivery Status: {matching_notif['status']}")
print(f"      Message Preview: {matching_notif['message']}")
assert matching_notif['status'] in ['sent', 'simulated']
assert demo_cid in matching_notif['message']

print("\nALL END-TO-END VERIFICATION CHECKS (INCLUDING FULL LIFECYCLE SCENARIO) PASSED PERFECTLY!")
