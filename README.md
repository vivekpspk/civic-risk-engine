# IMPACTX 2026 — Challenge 10: "Your City, Your Services"
## Explainable Civic Risk Scoring, Priority Engine & Complaint Lifecycle Backend
### Team OverClock | VIT-AP University

**Official GitHub Repository:** [https://github.com/vivekpspk/civic-risk-engine](https://github.com/vivekpspk/civic-risk-engine)  
**Clone URL:** `https://github.com/vivekpspk/civic-risk-engine.git`  
**Active Branch:** `main`  
**Automated Test Suite:** 65/65 Unit & Integration Tests Passing (100% Pass Rate)  
**Live UI & API Server:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/) | Swagger Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🤖 Instructions for Teammate's Antigravity AI Agent

If your teammate or their Antigravity agent is picking up this repository, copy and paste this exact prompt into their Antigravity chat:

```text
Act as a senior full-stack engineer on Team OverClock for IMPACTX 2026 Challenge 10 ("Your City, Your Services").
Our teammate has already built, tested, and verified the complete backend for the Civic Risk Scoring & Priority Engine and the 11-status Civic Complaint Lifecycle.

1. Clone our official repository:
   git clone https://github.com/vivekpspk/civic-risk-engine.git
   cd civic-risk-engine

2. Read TEAMMATE_ANTIGRAVITY_HANDOFF.md, INTEGRATION_GUIDE.md, and README.md.

3. DO NOT rewrite or break the existing 6-factor risk formula, safety override rules, evidence redaction pipeline, or lifecycle state machine.

4. Run the test suite to verify everything passes:
   cd backend
   python -m pytest tests -v

5. Start the full-stack server (serves the pre-built React UI + API):
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

6. Proceed to integrate our frontend, complementary microservices, or custom dashboard components with the documented REST endpoints.
```

---

## 1. System Overview & End-to-End Workflow

This repository provides the complete municipal backend for the entire civic incident and complaint lifecycle:

$$\text{Citizen Report (with Photo)} \longrightarrow \text{Auto Risk Triage} \longrightarrow \text{Admin Assigns Worker} \longrightarrow \text{Worker Resolves (After-Photo)} \longrightarrow \text{Admin Verifies} \longrightarrow \text{Citizen Before/After Proof \& SMS}$$

```
+---------------------------------------------------------------------------------------------------------+
|                                    CIVIC COMPLAINT LIFECYCLE WORKFLOW                                   |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|   1. CITIZEN SUBMISSION                                                                                 |
|      - POST /api/complaints                                                                             |
|      - Uploads issue description, GPS coordinates, optional contact info, SMS consent, and initial photo|
|      - Generates unguessable complaint ID (e.g. CIV-2026-A1B2C3D4)                                      |
|                                                                                                         |
|   2. AUTOMATIC RISK TRIAGE & SAFETY OVERRIDE                                                            |
|      - Evaluates deterministic 6-factor risk formula (Hazard, Proximity, Population, Weather, Time, C) |
|      - Evaluates safety overrides (e.g. open manholes near schools trigger Critical Emergency Review)   |
|      - Automatically sets status: ASSESSED & ranks into priority queue                                  |
|                                                                                                         |
|   3. ADMINISTRATOR ASSIGNMENT                                                                           |
|      - GET /api/admin/complaints & GET /api/admin/priority-queue                                        |
|      - POST /api/admin/complaints/{id}/assign                                                           |
|      - Assigns municipal worker (e.g. WRK-101) with task instructions and SLA target                    |
|      - Status transitions: ASSIGNED                                                                     |
|                                                                                                         |
|   4. FIELD WORKER TASK EXECUTION                                                                        |
|      - GET /api/worker/tasks (filtered by X-Worker-ID)                                                  |
|      - POST /api/worker/tasks/{id}/accept  --> Status: ACCEPTED                                         |
|      - POST /api/worker/tasks/{id}/start   --> Status: IN_PROGRESS                                      |
|      - (Or POST /api/worker/tasks/{id}/unable-to-resolve with blockers --> Status: UNABLE_TO_RESOLVE)   |
|                                                                                                         |
|   5. WORKER RESOLUTION & AFTER-PHOTO PROOF                                                              |
|      - POST /api/worker/complaints/{id}/evidence/after (uploads tamper-evident after-photos)            |
|      - POST /api/worker/tasks/{id}/submit-resolution                                                    |
|      - Status transitions: VERIFICATION_REQUIRED                                                       |
|                                                                                                         |
|   6. ADMINISTRATOR VERIFICATION AUDIT                                                                   |
|      - GET /api/complaints/{id}/comparison (inspects before vs. after proof side-by-side)               |
|      - POST /api/admin/complaints/{id}/verify-resolution (approved=true)                                |
|      - Validates after-evidence is present before allowing completion                                    |
|      - Status transitions: COMPLETED                                                                    |
|                                                                                                         |
|   7. CITIZEN PROOF & IDEMPOTENT SMS NOTIFICATION                                                        |
|      - GET /api/public/complaints/{id} (citizen tracks status timeline & before/after proof; 0 PII leak)|
|      - Automated SMS notification dispatched with idempotency key COMPL-RESOLVED-{id}                   |
|                                                                                                         |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Complete 11-Status Complaint Lifecycle State Machine

Status transitions are strictly validated on the server. Arbitrary jumps and unauthorized role transitions are rejected with HTTP 422:

| Status | Triggering Actor | Description | Permitted Next Statuses |
| :--- | :--- | :--- | :--- |
| `SUBMITTED` | Citizen | Complaint registered with initial evidence | `ASSESSED`, `ASSIGNED`, `REJECTED` |
| `ASSESSED` | Risk Engine | Risk score & safety overrides computed | `ASSIGNED`, `REJECTED` |
| `ASSIGNED` | Administrator | Assigned to field worker with instructions | `ACCEPTED`, `ASSIGNED`, `REJECTED` |
| `ACCEPTED` | Field Worker | Worker acknowledges dispatch | `IN_PROGRESS`, `UNABLE_TO_RESOLVE` |
| `IN_PROGRESS` | Field Worker | Physical on-site inspection or repair underway | `RESOLUTION_SUBMITTED`, `VERIFICATION_REQUIRED`, `UNABLE_TO_RESOLVE` |
| `RESOLUTION_SUBMITTED` | Field Worker | Work finished, after-photos uploaded | `VERIFICATION_REQUIRED` |
| `VERIFICATION_REQUIRED`| Worker / System | Awaiting admin review of resolution proof | `COMPLETED`, `IN_PROGRESS`, `REJECTED` |
| `COMPLETED` | Administrator | Resolution verified with before/after photos | `REOPENED` |
| `REOPENED` | Administrator | Work inadequate or recurring hazard reported | `ASSIGNED`, `IN_PROGRESS` |
| `REJECTED` | Administrator | Ineligible report with mandatory reason | None (terminal) |
| `UNABLE_TO_RESOLVE` | Field Worker | Legitimate site blocker with explanation | `ASSIGNED`, `REJECTED`, `IN_PROGRESS` |

### Strict Role Security Barriers:
- **Workers cannot approve their own work:** Any worker attempting to transition a task directly to `COMPLETED` is rejected with HTTP 403 Forbidden.
- **Workers cannot modify unassigned tasks:** Workers can only view and update tasks assigned to their authenticated `worker_id`.
- **Admin cannot complete without after-evidence:** Approving a resolution requires at least one verified after-photo on file.

---

## 3. Secure Before-and-After Evidence Management

- **Before Photos:** Uploaded by citizen upon submission (`POST /api/complaints/{id}/evidence/before`). Timestamped, actor-linked, and immutable.
- **After Photos:** Uploaded by assigned worker upon repair (`POST /api/worker/complaints/{id}/evidence/after`). Separate evidence tier.
- **Side-by-Side Comparison Dossier:** `GET /api/complaints/{id}/comparison` returns separated collections of before-photos and after-photos.
- **Tamper & File Signature Security:**
  - Validates binary magic bytes (JPEG `\xff\xd8`, PNG `\x89PNG`, WEBP `RIFF...WEBP`).
  - Max file size: 10 MB per photo. Max photos: 5 per submission.
  - Automatically scrubs EXIF metadata, GPS hardware tags, and camera serial numbers before serving.
  - Safe streaming endpoint (`GET /api/evidence/{id}/file`) prevents exposure of raw disk paths.

---

## 4. Deterministic 6-Factor Risk Formula

The core mathematical engine scores incidents from $0.0$ to $100.0$:

$$\text{Risk Score} = 100 \times (0.25H + 0.20S + 0.20P + 0.15W + 0.10T + 0.10C)$$

- **$H$ (Hazard Severity, 25%):** Mapped from civic taxonomy (e.g. `open_manhole`: 1.0, `severe_flooding`: 0.9, `pothole`: 0.3).
- **$S$ (Sensitive-Site Proximity, 20%):** Exponential distance decay from schools, hospitals, transit ($d \le 50\text{m} \implies 1.0$).
- **$P$ (Population Exposed, 20%):** Active density index. Missing data flagged as uncertainty; defaults to conservative planning baseline 0.50 (distinct from confirmed zero).
- **$W$ (Weather Risk, 15%):** Real-time precipitation and flood telemetry.
- **$T$ (Time Outstanding, 10%):** Linear escalation capped at 24 hours. Immediate emergencies never wait for this factor.
- **$C$ (Historical Recurrence, 10%):** Distinct past incidents in past 30 days. Duplicate reports for the same incident cluster do not inflate recurrence.

### Independent Safety Override Engine
Imminent life hazards (e.g. open manholes near schools, live wires submerged in water) immediately activate **Critical Emergency Review**, independent of raw numerical formula score.

---

## 5. Quick Start & Execution Guide

### Option A: Single-Command Full-Stack (Recommended)
The React frontend is pre-built into `frontend/dist/`. FastAPI automatically serves the complete interactive UI alongside the REST API:

```bash
# 1. Navigate to backend directory
cd backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start full-stack server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive Full-Stack Web App:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Service Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Seeded Field Workers for Testing:
- `WRK-101`: Ramesh Kumar (Drainage & Sewerage)
- `WRK-102`: Priya Sharma (Roads & Bridges)
- `WRK-103`: Suresh Reddy (Electrical & Lighting)
- `WRK-104`: Ananya Das (Sanitation & Health)

---

## 6. Running Automated Tests

Run the complete 65-test verification suite:

```bash
cd backend
python -m pytest tests -v
```

### Complete Test Coverage Breakdown (65/65 PASS):
1. **`test_complaint_lifecycle.py` (25/25 PASS):** Tests complete 11-status lifecycle, role enforcement, before/after evidence validation, SMS idempotency, citizen privacy, and audit trail.
2. **`test_complaint_engine.py` (22/22 PASS):** Tests complaint submission, automatic risk assessment, department routing, SLA deadlines, and duplicate report deduplication.
3. **`test_risk_engine.py` (14/14 PASS):** Tests 6-factor mathematical formula, exact Section 8 sample vector (74.0/100), safety overrides, 140-report stress simulator, and tie-breaking.
4. **`test_gemini_ai.py` (4/4 PASS):** Tests AI visual hazard analysis and fallback heuristics.

### Automated End-to-End Simulation Script:
Run the live 8-step citizen &rarr; worker &rarr; admin &rarr; citizen integration script:
```bash
python verify_e2e.py
```

---

## 7. Complete API Reference

### 1. Citizen & Public Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/complaints` | Citizen submits new complaint with photo, location, and SMS consent |
| `GET` | `/api/complaints/{id}` | Detailed complaint record with assessment & history |
| `GET` | `/api/public/complaints/{id}` | Privacy-safe citizen tracking portal (zero PII leaks) |
| `POST` | `/api/complaints/{id}/evidence/before` | Upload citizen before-resolution photos |
| `GET` | `/api/complaints/{id}/evidence` | List all verified evidence records |
| `GET` | `/api/complaints/{id}/comparison` | Side-by-side Before vs. After proof comparison dossier |
| `GET` | `/api/evidence/{id}/file` | Safe sanitized image byte stream (strips EXIF) |

### 2. Field Worker Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/worker/tasks` | List tasks assigned to worker (`?worker_id=WRK-101`) |
| `GET` | `/api/worker/tasks/{id}` | Detailed task instructions, location, and severity |
| `POST` | `/api/worker/tasks/{id}/accept` | Worker accepts dispatch (`ASSIGNED` &rarr; `ACCEPTED`) |
| `POST` | `/api/worker/tasks/{id}/start` | Worker starts physical repair (`ACCEPTED` &rarr; `IN_PROGRESS`) |
| `POST` | `/api/worker/complaints/{id}/evidence/after` | Worker uploads after-repair proof photos |
| `POST` | `/api/worker/tasks/{id}/submit-resolution` | Worker submits completion & after-photos for verification |
| `POST` | `/api/worker/tasks/{id}/unable-to-resolve` | Worker reports on-site blocker with reason |

### 3. Administrator Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/admin/complaints` | List all complaints with filter by status & priority |
| `GET` | `/api/admin/priority-queue` | Dynamic triage queue sorted by Override &rarr; Risk &rarr; SLA &rarr; Age |
| `GET` | `/api/admin/dashboard` | Municipal statistics, SLA breach counts, worker workload |
| `GET` | `/api/admin/workers` | Municipal worker roster and current active assignments |
| `POST` | `/api/admin/complaints/{id}/assign` | Assign worker with specific instructions and target SLA |
| `POST` | `/api/admin/complaints/{id}/verify-resolution` | Verify resolution (approves to `COMPLETED` & sends SMS, or rejects back) |
| `POST` | `/api/admin/complaints/{id}/reopen` | Reopen completed complaint with reason |
| `POST` | `/api/admin/complaints/{id}/reject` | Reject invalid complaint with mandatory reason |
| `GET` | `/api/admin/notifications` | Audit log of dispatched citizen SMS notifications |

### 4. Risk Engine & Simulation Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health status, formula version, and active factor weights |
| `POST` | `/incidents` | Create incident and calculate risk |
| `POST` | `/incidents/{id}/assess` | Recalculate 6-factor risk score |
| `GET` | `/priority-queue` | Priority queue endpoint |
| `POST` | `/simulation/run-140-reports` | Execute 140-report storm stress test |
| `GET` | `/simulation/status` | Simulation metrics and cluster statistics |

---

## 8. Project Directory Structure

```text
civic_risk_engine/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entrypoint, CORS, static UI mount
│   │   ├── config.py                # Weights, priority bands, hazard taxonomy, safety rules
│   │   ├── core/
│   │   │   ├── lifecycle.py         # 11-status state machine & role permission matrix
│   │   │   ├── risk_scorer.py       # 6-factor deterministic calculation & contributions
│   │   │   ├── feature_extractor.py # Feature extraction, GIS decay, missing data handling
│   │   │   ├── safety_rules.py      # Independent safety override engine
│   │   │   └── priority_engine.py   # Deterministic queue ranking & SLA tracking
│   │   ├── models/
│   │   │   ├── database.py          # SQLAlchemy models (Complaint, Evidence, Worker, Assignment)
│   │   │   └── schemas.py           # Pydantic validation schemas
│   │   ├── services/
│   │   │   ├── evidence_service.py  # Evidence upload, EXIF stripping, MIME signature validation
│   │   │   ├── storage_service.py   # Secure disk storage adapter & streaming
│   │   │   ├── worker_service.py    # Worker task management & resolution submissions
│   │   │   ├── admin_service.py     # Worker assignment, verification audit & reopening
│   │   │   ├── notification_service.py # Idempotent citizen SMS notifications
│   │   │   ├── incident_service.py  # Incident lifecycle, persistence, audit logging
│   │   │   └── simulation_service.py# 140-report generator & scenario clustering
│   │   └── api/
│   │       ├── complaints_api.py    # Citizen complaint submission & tracking
│   │       ├── evidence_api.py      # Photo upload, comparison dossier & streaming
│   │       ├── worker_api.py        # Worker dispatch, progress & resolution APIs
│   │       ├── admin_api.py         # Administrator assignment & verification APIs
│   │       ├── public_api.py        # Privacy-safe citizen public tracking portal
│   │       ├── incidents.py         # Incident endpoints
│   │       ├── priority.py          # Priority queue endpoint
│   │       ├── config_api.py        # Model configuration endpoints
│   │       └── simulation.py        # Scenario simulator endpoints
│   ├── tests/
│   │   ├── test_complaint_lifecycle.py # 25 automated lifecycle & permission tests
│   │   ├── test_complaint_engine.py    # 22 complaint submission & queue tests
│   │   ├── test_risk_engine.py         # 14 mathematical risk formula tests
│   │   └── test_gemini_ai.py           # 4 AI visual assessment tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # Main layout & tab router
│   │   ├── index.css                # Light-mode glassmorphism styling
│   │   ├── types/index.ts           # TypeScript interfaces
│   │   ├── api/client.ts            # Fetch API client
│   │   └── components/
│   │       ├── Navbar.tsx           # Brand, health indicator, tab switcher
│   │       ├── RiskCalculator.tsx   # Interactive 6-factor live calculator
│   │       ├── PriorityQueue.tsx    # Multi-tier ranked queue & inspector
│   │       ├── IncidentDetail.tsx   # Dossier, Before/After proof & dispatch modal
│   │       └── ScenarioSimulator.tsx# 140-report stress test dashboard
│   ├── dist/                        # Production pre-built frontend assets
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── TEAMMATE_ANTIGRAVITY_HANDOFF.md  # Dedicated Antigravity prompt & handoff document
├── INTEGRATION_GUIDE.md             # Developer integration guide & JSON payloads
├── verify_e2e.py                    # Complete end-to-end integration verifier
├── .env.example                     # Environment configuration template
└── README.md                        # Primary documentation & setup guide
```

---
*Built for Team OverClock | IMPACTX 2026 Challenge 10: "Your City, Your Services" | VIT-AP University.*
