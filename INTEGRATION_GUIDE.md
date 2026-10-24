# IMPACTX 2026 — Challenge 10: Your City, Your Services
## Team OverClock | Backend Integration Guide & API Contracts
**Service:** Explainable Civic Risk Scoring & Priority Engine  
**Institution:** VIT-AP University  
**Formula Version:** `v1.0.0` (`Risk Score = 100 * (0.25H + 0.20S + 0.20P + 0.15W + 0.10T + 0.10C)`)

---

## 1. System Architecture & Modular Boundaries

The civic risk engine is designed as a standalone, modular microservice that accepts civic complaints from mobile/web frontends or external team backends, derives all risk factors automatically without user math, applies deterministic safety overrides, and outputs an explainable, ranked priority queue.

```
                           [ Citizen Complaint ]
                  (Text, GPS/Address, Photo Evidence)
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │                   AUTOMATIC FACTOR EXTRACTION                   │
 ├────────────────────────────────┬────────────────────────────────┤
 │ H: 24 Rain Hazards Taxonomy    │ S: Geodesic Sensitive Distance │
 │ P: Population Exposure Model   │ W: Cached Weather / Doppler    │
 │ T: Time Elapsed Escalation     │ C: Distinct Ward Recurrence    │
 └────────────────────────────────┴────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │          DETERMINISTIC CIVIC RISK SCORING FORMULA               │
 │    R = 100 × (0.25H + 0.20S + 0.20P + 0.15W + 0.10T + 0.10C)    │
 └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │               INDEPENDENT SAFETY OVERRIDE ENGINE                │
 │   RULE-001 (Open Manhole near School)                           │
 │   RULE-002 (Live Wire in Floodwater)                            │
 │   RULE-005 (Trapped People in Flood)                            │
 │   RULE-006 (Imminent Collapse / Sinkhole)                       │
 └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │         WARD ROUTING, DISPUTE DETECTION & SLA DEADLINES         │
 ├────────────────────────────────┬────────────────────────────────┤
 │ Ward Jurisdiction Resolution   │ Cross-Ward Dispute Flagging    │
 │ Responsible Dept Assignment    │ SLA Deadline Calculation       │
 └────────────────────────────────┴────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │                 DYNAMIC ADMINISTRATOR QUEUE                     │
 │   1. Active Safety Overrides -> 2. Risk Score ->                │
 │   3. SLA Urgency -> 4. Incident Age (Tie-Breaker)               │
 └─────────────────────────────────────────────────────────────────┘
```

---

## 2. API Endpoints & Contract Specifications

### 2.1 Citizen Complaint Intake
**Endpoint:** `POST /api/complaints`  
**Description:** Accepts natural citizen reports without asking citizens to calculate risk or rate severity.

#### Request Body (`application/json`):
```json
{
  "description": "Water is accumulating near a school, and an uncovered manhole is visible during heavy rain.",
  "latitude": 16.5063,
  "longitude": 80.6481,
  "location_address": "Near St. Mary's School Gate",
  "hazard_category_hint": "open_manhole",
  "evidence_photos": ["photo1.jpg"],
  "reporter_name": "Aadi Desai",
  "reporter_phone": "+91-9876543210",
  "reporter_email": "aadi@example.com",
  "consent_given": true
}
```

#### Response Body (`201 Created`):
```json
{
  "complaint_id": "CMP-2026-D2A6",
  "status": "submitted",
  "hazard_category": "open_manhole",
  "hazard_display_name": "Open or Uncovered Manhole",
  "risk_score": 78.5,
  "priority_band": "Critical",
  "assigned_department": "Drainage & Sewerage Department",
  "assigned_ward": "Ward 07",
  "is_boundary_dispute": false,
  "disputed_wards": [],
  "sla_deadline": "2026-10-24T07:38:29.043Z",
  "estimated_response_window": "Immediate Dispatch (1.0 Hours SLA)",
  "plain_language_explanation": "SAFETY OVERRIDE ACTIVATED: Open manhole in high-proximity zone (<100m) of school triggers mandatory safety override for immediate dispatch. • Classified as 'Open or Uncovered Manhole' with physical hazard severity 1.00. • Nearest facility 'St. Mary's Public School' is 15.2m away. • Estimated 382 persons exposed within 50m radius. • Doppler radar telemetry: 65.0 mm/hr.",
  "recommended_action": "Dispatch emergency cordoning squad immediately; place retroreflective barricades and temporary safety mesh.",
  "safety_override_active": true,
  "evidence_status": "reported",
  "tracking_url": "/api/complaints/CMP-2026-D2A6",
  "submitted_at": "2026-10-24T06:38:29.043Z"
}
```
*Note: Public response strictly omits reporter phone, email, and private contact information.*

---

### 2.2 Public Complaint Status Tracking
**Endpoint:** `GET /api/complaints/{complaint_id}`  
**Description:** Publicly queryable status endpoint for citizens. Strips all reporter PII.

---

### 2.3 Detailed Risk Assessment Query
**Endpoint:** `GET /api/complaints/{complaint_id}/risk`  
**Description:** Retrieves the factor-level breakdown, sources, and uncertainty flags.

#### Response Body (`200 OK`):
```json
{
  "incident_id": "CMP-2026-D2A6",
  "risk_score": 78.5,
  "priority_band": "Critical",
  "safety_override": {
    "active": true,
    "effective_severity": "Critical",
    "triggered_rules": [
      {
        "rule_id": "RULE-001",
        "rule_name": "School/Sensitive Site Open Manhole Chamber",
        "condition_matched": "Open manhole with proximity to sensitive site >= 0.70",
        "severity_level": "Critical",
        "trigger_result": "CRITICAL_REVIEW"
      }
    ]
  },
  "factor_contributions": {
    "hazard_severity": 25.0,
    "sensitive_site_proximity": 20.0,
    "population_exposed": 7.6,
    "weather_risk": 9.8,
    "time_outstanding": 0.0,
    "recurrence": 2.0
  },
  "uncertainty_flags": [],
  "sla_status": "within_sla",
  "recommended_action": "Dispatch emergency cordoning squad immediately."
}
```

---

### 2.4 Administrator Priority Queue
**Endpoint:** `GET /api/admin/priority-queue?limit=100`  
**Description:** Deterministically ranked municipal operational queue.

Ranking Order:
1. **Active Safety Overrides First** (Urgent life-safety reviews)
2. **Physical Risk Score** (Highest to lowest)
3. **SLA Urgency** (Breached > Imminent > Within SLA)
4. **Age Tie-Breaker** (Oldest unresolved complaints first)

---

### 2.5 Administrator Dashboard Telemetry
**Endpoint:** `GET /api/admin/dashboard`  
**Description:** Real-time counts of Total Complaints, Priority Bands (Critical, High, Medium, Routine), Awaiting Verification, Safety Overrides, SLA Breaches, and Boundary Disputes directly from SQLite database.

---

### 2.6 Authorized Safety Override
**Endpoint:** `POST /api/admin/complaints/{complaint_id}/override`  
**Description:** Promotes an incident's priority with mandatory authorization credentials and tamper-evident audit logging.

#### Request Body:
```json
{
  "authorized_by": "Commissioner R. Sharma",
  "role": "municipal_commissioner",
  "reason": "Emergency child safety protocol activation during storm dismissal.",
  "target_severity": "Critical"
}
```

---

### 2.7 Ward Reassignment & Boundary Dispute Resolution
**Endpoint:** `PATCH /api/admin/complaints/{complaint_id}/assignment`  
#### Request Body:
```json
{
  "assigned_department": "Roads & Bridges Department",
  "assigned_ward": "Ward 07",
  "authorized_by": "Duty Officer S. Murthy",
  "reason": "Joint border inspection confirmed asset lies on Ward 07 arterial lane."
}
```

---

### 2.5 Google Gemini AI Automated Analysis & Triage
**Endpoint:** `POST /api/ai/analyze`  
**Description:** Direct API for submitting unstructured complaint text and receiving real-time Gemini AI hazard inference, emergency safety cues, population vulnerability estimation, and explainable narrative summaries.

#### Request Body (`application/json`):
```json
{
  "description": "Water is accumulating near a school, and an uncovered manhole is visible during heavy rain.",
  "location": "Near St. Mary's School Gate, Ward 07",
  "category_hint": "open_manhole"
}
```

#### Response Body:
```json
{
  "detected_hazard_type": "open_manhole",
  "hazard_title": "Open or Uncovered Manhole",
  "hazard_severity": 0.95,
  "emergency_safety_override": true,
  "emergency_rule_candidate": "RULE-001",
  "sensitive_site_cues": ["school"],
  "population_exposure_cues": "high",
  "recommended_department": "Drainage & Sewerage Department",
  "recommended_urgency": "Critical",
  "ai_reasoning_summary": "An open manhole near a school during heavy rain creates an extreme, immediate life-safety hazard for children and pedestrians due to high risk of falls and drowning in murky water. Emergency dispatch is required to barricade the area and deploy rapid response crews to cover the manhole.",
  "ai_model_used": "gemini-3.5-flash-lite",
  "analysis_status": "gemini_analyzed",
  "confidence_score": 0.95
}
```

**Status Endpoint:** `GET /api/ai/status`  
Returns active model info, fallback models (`gemini-3.1-flash-lite`, `gemini-3.6-flash`, `gemini-3.5-flash`), and key configuration status.

---

## 3. How Teammates Can Plug In Replaceable Adapters

### 3.1 Custom Live Weather Provider
Implement the `IWeatherProvider` interface in `backend/app/core/weather_service.py`:
```python
class OpenWeatherMapProvider(IWeatherProvider):
    def get_weather_risk(self, latitude, longitude, ward=None) -> WeatherData:
        # Call live API, cache results, handle network failures
        ...
```
Assign `app.core.weather_service.default_weather_provider = OpenWeatherMapProvider()`.

### 3.2 Custom GIS & Facilities Provider
Extend `GISService` in `backend/app/core/gis_service.py` with your city's GeoJSON boundary polygons or ArcGIS layer.

### 3.3 Google Gemini AI Integration
Configured via `.env`:
```bash
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```
Service located at [`backend/app/services/gemini_service.py`](file:///C:/Users/vivek/.gemini/antigravity/scratch/impactx-overclock/civic_risk_engine/backend/app/services/gemini_service.py). Automatically fails over between Gemini models on cloud demand spikes and provides seamless zero-downtime deterministic heuristic fallback.

---

## 4. Privacy, Abuse Resistance & Security Summary

1. **EXIF Scrubbing:** All photos uploaded to `/api/complaints` are automatically stripped of GPS coordinates, camera serial numbers, and metadata via `evidence_service.py` before storage.
2. **Contact Protection:** Public endpoints (`GET /api/complaints/{id}`) strictly redact reporter names, telephone numbers, and email addresses.
3. **Coordinated Spam Resistance:** Duplicate reports from the same location/cluster contribute to evidence corroboration without artificially inflating the mathematical recurrence score (`C`).
4. **Preservation of Genuine Hazards:** Even during coordinated bot attacks, genuine emergency overrides (`RULE-001` - `RULE-006`) are processed immediately and preserved at the top of the queue.

---

## 5. Verification Commands

```powershell
# Run backend pytest suite (40 tests)
cd backend
python -m pytest tests -v

# Run end-to-end Python client verification
cd ..
python verify_e2e.py

# Launch FastAPI backend with interactive Swagger UI
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Swagger API Documentation: **http://127.0.0.1:8000/docs**
