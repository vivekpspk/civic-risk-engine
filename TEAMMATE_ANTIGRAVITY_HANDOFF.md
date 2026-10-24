# TEAM OVERCLOCK | ANTIGRAVITY AGENT HANDOFF PROMPT
## IMPACTX 2026 — Challenge 10: "Your City, Your Services"
### Project: Civic Risk Scoring, Priority Engine & Complaint Lifecycle Backend
**Official GitHub Repository:** [https://github.com/vivekpspk/civic-risk-engine](https://github.com/vivekpspk/civic-risk-engine)  
**Clone URL:** `https://github.com/vivekpspk/civic-risk-engine.git`  
**Active Branch:** `main`  
**Test Coverage:** 65/65 Automated Tests Passing (100% Pass Rate)

---

## 1. Instructions for Teammate's Antigravity Agent

When you start your session with Antigravity, paste the following prompt:

```text
Act as a senior full-stack engineer on Team OverClock for IMPACTX 2026 Challenge 10.
Our teammate has already built and verified the complete backend for the Civic Risk Scoring & Priority Engine and Complaint Lifecycle.
First, clone our official repository:
git clone https://github.com/vivekpspk/civic-risk-engine.git
Read TEAMMATE_ANTIGRAVITY_HANDOFF.md and INTEGRATION_GUIDE.md before changing any code.
Do not rewrite or modify the working risk calculation formula, safety override rules, or lifecycle state machine.
Integrate our frontend and complementary services with this backend following the documented API contracts.
```

---

## 2. What Is Already Fully Implemented & Verified

You do NOT need to rebuild the backend. The following components are 100% complete and tested:

### 1. Deterministic 6-Factor Civic Risk Scoring Engine
- Formula: $\text{Risk Score} = 100 \times (0.25H + 0.20S + 0.20P + 0.15W + 0.10T + 0.10C)$
- $H$: 24-category severe rain hazard taxonomy.
- $S$: Geodesic sensitive-site proximity decay (schools, hospitals, transit).
- $P$: Active population exposure index (flags missing data without assuming zero).
- $W$: Real-time precipitation & Doppler telemetry.
- $T$: Capped time-elapsed escalation (max 24 hours).
- $C$: 30-day historical ward recurrence (duplicate storm reports do not inflate recurrence).
- Verified Section 8 Test Vector: Inputs $(1.0, 0.9, 0.7, 0.8, 0.2, 0.3) \implies 74.0 / 100$ (Critical / High).

### 2. Independent Safety Override Engine
- Imminent life hazards (e.g. open manholes near schools, live wires submerged in water) immediately activate emergency review, independent of raw numerical score.

### 3. Dynamic Administrator Priority Queue
- Deterministic hierarchy: `Active Safety Override` $\to$ `Physical Risk Score` $\to$ `SLA Urgency` $\to$ `Oldest Incident Age`.

### 4. 140-Report Storm Scenario Simulator
- Ingests exactly 140 reports across 3 simulated storm hours (28 school manhole, 36 boundary waterlogging, 32 bot attack, 44 routine issues) while preserving independent genuine emergencies in the top 2 queue slots.

### 5. Complete Complaint Lifecycle State Machine (11 Statuses)
- Controlled validated transitions:
  `SUBMITTED` $\to$ `ASSESSED` $\to$ `ASSIGNED` $\to$ `ACCEPTED` $\to$ `IN_PROGRESS` $\to$ `VERIFICATION_REQUIRED` $\to$ `COMPLETED`
  (with support for `REOPENED`, `REJECTED`, and `UNABLE_TO_RESOLVE`).
- **Strict Role Security:** Field workers **cannot** approve their own work as `COMPLETED`. Administrator verification is mandatory.

### 6. Secure Before-and-After Evidence Management
- Automatic MIME signature validation (JPEG, PNG, WEBP) and 10MB limits.
- EXIF metadata and GPS hardware tags stripped from public copies.
- Strictly separated storage for before-photos and after-photos.
- Side-by-side comparison contract (`GET /api/complaints/{id}/comparison`).
- Safe streaming endpoint (`GET /api/evidence/{id}/file`) prevents exposure of raw disk paths.

### 7. Resilient Idempotent SMS Notification Service
- Triggered **only** when an administrator verifies a complaint as `COMPLETED`.
- Unique idempotency key (`COMPL-RESOLVED-{complaint_id}`) prevents duplicate SMS charges.
- Respects citizen consent (`consent_sms`); notification failures never roll back completion.
- Defaults to `MockNotificationProvider` (simulated delivery, 100% offline). Configurable for live Twilio.

### 8. Citizen Public Tracking Portal
- Accessible via unguessable ID `CIV-2026-XXXXXXXX` (`GET /api/public/complaints/{id}`).
- Returns status timeline, before-and-after proof photos, and resolution summary.
- **Privacy Guaranteed:** Never leaks citizen phone, email, worker contact, or internal admin notes.

---

## 3. Quick Start & Execution Commands

### Step 1: Clone Repository
```bash
git clone https://github.com/vivekpspk/civic-risk-engine.git
cd civic-risk-engine
```

### Step 2: Install Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 3: Start the Backend Server
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Interactive Full-Stack Web App:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Step 4: Run Automated Tests
```bash
# Run all 65 unit and integration tests (100% pass rate)
python -m pytest -v

# Run the live 8-step citizen -> worker -> admin -> citizen verification script
cd ..
python verify_e2e.py
```

---

## 4. Key API Contracts for Teammate Integration

### 1. Citizen Complaint Submission
- **POST** `/api/complaints`
```json
{
  "description": "Water accumulating near school, uncovered manhole visible during heavy rain.",
  "latitude": 16.5063,
  "longitude": 80.6481,
  "location_address": "Near St. Mary's School Gate, Ward 07",
  "hazard_category_hint": "open_manhole",
  "reporter_name": "Citizen Reporter",
  "reporter_phone": "+91-9876543210",
  "consent_sms": true
}
```
**Response (201 Created):**
```json
{
  "complaint_id": "CIV-2026-XXXXXXXX",
  "status": "submitted",
  "risk_score": 78.5,
  "priority_band": "Critical",
  "assigned_department": "Drainage & Sewerage Department",
  "assigned_ward": "Ward 07",
  "sla_deadline": "2026-10-24T07:38:29.043Z",
  "estimated_response_window": "Immediate Dispatch (1.0 Hours SLA)",
  "plain_language_explanation": "SAFETY OVERRIDE ACTIVATED: Open manhole in high-proximity zone (<100m) of school triggers mandatory safety override for immediate dispatch.",
  "safety_override_active": true,
  "tracking_url": "/api/public/complaints/CIV-2026-XXXXXXXX"
}
```

### 2. Evidence Upload & Side-by-Side Comparison
- **POST** `/api/complaints/{id}/evidence/before`: Upload citizen initial before-photo.
- **POST** `/api/worker/complaints/{id}/evidence/after`: Upload worker after-repair photo (requires `X-Worker-ID` header).
- **GET** `/api/complaints/{id}/comparison`: Returns separated `before_evidence` and `after_evidence` collections for side-by-side display.
- **GET** `/api/evidence/{evidence_id}/file`: Streams sanitized image bytes.

### 3. Field Worker Operations
- **GET** `/api/worker/tasks?worker_id=WRK-101`: List tasks assigned to worker.
- **POST** `/api/worker/tasks/{id}/accept`: Worker accepts task (`ASSIGNED` $\to$ `ACCEPTED`).
- **POST** `/api/worker/tasks/{id}/start`: Worker commences work (`ACCEPTED` $\to$ `IN_PROGRESS`).
- **POST** `/api/worker/tasks/{id}/unable-to-resolve`: Report blocker (`IN_PROGRESS` $\to$ `UNABLE_TO_RESOLVE`).
- **POST** `/api/worker/tasks/{id}/submit-resolution`: Submit completion with after-photo IDs (`IN_PROGRESS` $\to$ `VERIFICATION_REQUIRED`).

### 4. Administrator Operations
- **GET** `/api/admin/priority-queue`: Prioritized queue (Overrides $\to$ Risk Score $\to$ SLA $\to$ Age).
- **GET** `/api/admin/workers`: List registered workers and active task counts.
- **POST** `/api/admin/complaints/{id}/assign`: Assign worker (`worker_id`, `admin_id`, `instructions`).
- **POST** `/api/admin/complaints/{id}/verify-resolution`:
  - `{"decision": "approve", "admin_id": "...", "notes": "..."}`: Marks `COMPLETED` and dispatches citizen SMS.
  - `{"decision": "reject", "admin_id": "...", "notes": "..."}`: Returns task to `IN_PROGRESS` for rework.
- **POST** `/api/admin/complaints/{id}/reopen`: Reopen completed complaint (`admin_id`, `reason`).
- **GET** `/api/admin/notifications`: SMS audit history and delivery status.

### 5. Citizen Public Status Tracking
- **GET** `/api/public/complaints/{id}`: Public dossier containing status timeline, approved before/after photos, and resolution description without exposing private contact info.

---

## 5. Seeded Municipal Field Workers (Ready for Testing)

| Worker ID | Name | Department | Ward |
| :--- | :--- | :--- | :--- |
| `WRK-101` | Ramesh Kumar | Stormwater Drainage & Flood Control | Ward 07 |
| `WRK-102` | Priya Sharma | Roads & Infrastructure Maintenance | Ward 03 |
| `WRK-103` | Suresh Reddy | Electrical & Public Safety | Ward 12 |
| `WRK-104` | Ananya Das | Water Supply & Sewerage Board | Ward 07 |

---

## 6. Architecture & Directory Tree

```text
civic-risk-engine/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entrypoint, CORS, static frontend mount
│   │   ├── config.py                # Formula weights, priority bands, hazard taxonomy, safety rules
│   │   ├── core/
│   │   │   ├── lifecycle.py         # 11-status state machine, transition & role validator
│   │   │   ├── risk_scorer.py       # Deterministic 6-factor risk calculation & points breakdown
│   │   │   ├── feature_extractor.py # GIS decay, population estimation, weather integration
│   │   │   ├── safety_rules.py      # Independent emergency override engine
│   │   │   ├── priority_engine.py   # Deterministic queue ranking & SLA tracking
│   │   │   └── hazard_taxonomy.py   # 24-category severe rain hazard taxonomy
│   │   ├── models/
│   │   │   ├── database.py          # SQLAlchemy models (Incident, Evidence, Worker, Assignment, Resolution, History, Notification)
│   │   │   └── schemas.py           # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── complaint_service.py # Citizen complaint intake & public tracking
│   │   │   ├── worker_service.py    # Field worker task workflow
│   │   │   ├── admin_service.py     # Administrator dispatch & verification
│   │   │   ├── evidence_service.py  # MIME signature validation & EXIF metadata stripping
│   │   │   ├── storage_service.py   # Storage provider adapter (local disk / cloud S3)
│   │   │   ├── notification_service.py # Idempotent SMS notification service
│   │   │   ├── gemini_service.py    # Automated spatial NLP triage & failover
│   │   │   ├── incident_service.py  # Incident dossier & manual override ledger
│   │   │   └── simulation_service.py# 140-report storm scenario simulator
│   │   └── api/
│   │       ├── complaints.py        # Citizen intake & public status
│   │       ├── evidence_api.py      # Before/after photo uploads & comparison
│   │       ├── worker_api.py        # Worker task workflow endpoints
│   │       ├── admin_api.py         # Admin dispatch, verification & notifications
│   │       ├── public_api.py        # Citizen public tracking endpoint
│   │       ├── incidents.py         # Physical incident assessment endpoints
│   │       ├── priority.py          # Dynamic priority queue endpoint
│   │       ├── config_api.py        # Formula weights & band configuration
│   │       └── simulation.py        # 140-report stress test endpoint
│   ├── tests/
│   │   ├── test_complaint_lifecycle.py # 25 lifecycle automated tests
│   │   ├── test_complaint_engine.py    # 22 intake & taxonomy tests
│   │   ├── test_risk_engine.py         # 14 risk formula & queue tests
│   │   └── test_gemini_ai.py           # 4 AI triage & spatial prompt tests
│   └── requirements.txt
├── frontend/                        # React 18, TypeScript, Tailwind CSS
│   ├── src/                         # Source components & API client
│   └── dist/                        # Production build served by FastAPI at '/'
├── verify_e2e.py                    # Complete 8-step end-to-end integration verifier
├── INTEGRATION_GUIDE.md             # In-depth API specification & contracts
├── TEAMMATE_ANTIGRAVITY_HANDOFF.md  # Teammate handoff guide
├── .env.example                     # Environment template with placeholder values
└── README.md                        # Master project documentation
```

---
*Built by Team OverClock | IMPACTX 2026 Challenge 10: "Your City, Your Services" | VIT-AP University.*
