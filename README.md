# IMPACTX 2026 — Challenge 10: "Your City, Your Services"
## Explainable Civic Risk Scoring & Priority Engine
### Team OverClock | VIT-AP University

A production-grade, mathematically deterministic, and explainable **Civic Risk Scoring and Priority Engine** built for municipal incident triage during severe weather emergencies.

---

## 1. System Overview

When sudden cloudbursts generate 140+ simultaneous civic reports across municipal wards, traditional first-in-first-out (FIFO) ticketing queues fail: fatal hazards remain buried beneath cosmetic complaints, inter-departmental boundary disputes stall response, and bot bursts divert emergency resources.

This platform implements:
1. **Complete Complaint Lifecycle State Machine:** Enforces strict validated transitions across 11 stages (`SUBMITTED`, `ASSESSED`, `ASSIGNED`, `ACCEPTED`, `IN_PROGRESS`, `RESOLUTION_SUBMITTED`, `VERIFICATION_REQUIRED`, `COMPLETED`, `REOPENED`, `REJECTED`, `UNABLE_TO_RESOLVE`).
2. **Secure Before-and-After Evidence Management:** Automatically strips EXIF metadata, verifies MIME signatures (JPEG, PNG, WEBP), and stores before-and-after proof separately for tamper-evident review.
3. **Role-Enforced Workflows:** Field workers cannot approve their own tasks or mark complaints completed. Administrator verification with before/after comparison is mandatory.
4. **Resilient Citizen SMS Notification:** Triggers completion SMS notifications to citizens upon administrator verification, protected by idempotency keys and citizen consent checks.
5. **Deterministic 6-Factor Risk Formula:** Dynamically scores incidents from 0.0 to 100.0 based on physical hazard severity, sensitive site proximity, population exposure, weather risk, elapsed time, and historical recurrence.
6. **Independent Safety Override Engine:** Automatically forces imminent life hazards (e.g., open manholes near school gates, sparking electrical cables in rainwater) to **Critical Emergency Review**, independent of raw formula scores.
7. **Dynamic Priority Queue:** Orders tickets using a strict hierarchy: `Active Safety Override` &rarr; `Physical Risk Score` &rarr; `SLA Urgency` &rarr; `Incident Age (Tie-Breaker)`.
8. **Honest Uncertainty & Missing Data Handling:** Distinctly differentiates zero population from missing census data, flagging uncertainties without making false assumptions.
9. **Replayable 140-Report Stress Test:** Ingests exactly 140 synthetic reports across 3 simulated storm hours while preserving independent genuine emergencies.
10. **Immutable Audit Ledger:** Persists every assessment, status transition, evidence upload, and authorized override.

---

## 2. Technology Stack

- **Backend:** Python 3.11+, FastAPI (Async ASGI framework).
- **Frontend:** React 18, TypeScript, Tailwind CSS (Vite build system).
- **UI Design:** Light-mode glassmorphism with white translucent cards, pastel blue, mint, lavender, and coral accents, accessible contrast, and smooth transitions.
- **Database:** SQLite for standalone zero-configuration local prototyping via SQLAlchemy 2.0 (structured for zero-friction migration to PostgreSQL + PostGIS).
- **Testing:** pytest with 14 automated unit and integration tests (100% pass rate).
- **Documentation:** Interactive OpenAPI / Swagger UI at `/docs`.

---

## 3. Mathematical Risk Scoring Model

The core engine computes risk according to the weighted formula:

$$\text{Risk Score} = 100 \times (0.25H + 0.20S + 0.20P + 0.15W + 0.10T + 0.10C)$$

Where all factors are normalized between $0.0$ and $1.0$:
- **$H$ (Hazard Severity, 25%):** Mapped from civic hazard taxonomy (e.g., `open_manhole`: 1.0, `severe_flooding`: 0.9, `pothole`: 0.3).
- **$S$ (Sensitive-Site Proximity, 20%):** Exponential distance decay from schools, hospitals, transit hubs ($d \le 50\text{m} \implies 1.0$).
- **$P$ (Population Exposed, 20%):** Active pedestrian/commuter density index. Missing data is flagged with an uncertainty warning and defaults to conservative planning baseline 0.50 (distinct from confirmed zero).
- **$W$ (Weather Risk, 15%):** Real-time precipitation and flash-flood susceptibility index. Stale feeds are flagged.
- **$T$ (Time Outstanding, 10%):** Linear escalation capped at 24 hours ($T = \min(1.0, \text{elapsed\_hours} / 24)$). Immediate emergencies never wait for this factor to rise.
- **$C$ (Historical Recurrence, 10%):** Distinct past incidents at the asset in the past 30 days. Duplicate reports for the same incident cluster do **not** inflate recurrence.

### Exact Section 8 Verification Test Case:
- **Inputs:** $H=1.0, S=0.9, P=0.7, W=0.8, T=0.2, C=0.3$
- **Calculation:** $100 \times (0.25 \times 1.0 + 0.20 \times 0.9 + 0.20 \times 0.7 + 0.15 \times 0.8 + 0.10 \times 0.2 + 0.10 \times 0.3)$
- **Contributions:** $H = 25.0, S = 18.0, P = 14.0, W = 12.0, T = 2.0, C = 3.0$
- **Result:** **`74.0 / 100`** (**High Priority Band**). Verified via automated pytest test `test_01_correct_weighted_score_calculation`.

### Configurable Priority Bands:
- **80.0 – 100.0:** Critical (Immediate response within 30 min)
- **60.0 – 79.99:** High (Response within 2 hours)
- **35.0 – 59.99:** Medium (Standard daily maintenance shift)
- **0.0 – 34.99:** Routine (Backlog intake within 72 hours)

*Disclaimer: A numerical score represents comparative operational triage urgency, not the physical probability of an accident.*

---

## 4. Quick Start & Execution Guide

### Option A: Single-Command Full-Stack (Recommended)
Because the React frontend is pre-built into `frontend/dist/`, running FastAPI automatically serves both the complete interactive web UI and the API:

```bash
# Navigate to the backend directory
cd C:\Users\vivek\.gemini\antigravity\scratch\impactx-overclock\civic_risk_engine\backend

# Start the full-stack server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser at:
- **Interactive Web Application:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Option B: Dual-Terminal Development Mode (Hot-Reloading)

**Terminal 1 (Backend API):**
```bash
cd C:\Users\vivek\.gemini\antigravity\scratch\impactx-overclock\civic_risk_engine\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 (Frontend Dev Server):**
```bash
cd C:\Users\vivek\.gemini\antigravity\scratch\impactx-overclock\civic_risk_engine\frontend
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) for instant hot-module replacement.

---

## 5. Running Automated Tests

Execute the 14-point test suite with pytest:

```bash
cd C:\Users\vivek\.gemini\antigravity\scratch\impactx-overclock\civic_risk_engine\backend
python -m pytest tests -v
```

### Verified Acceptance Test Suite (14/14 PASS):
- `test_01_correct_weighted_score_calculation`: Verified exact 74.0/100 sample match and contributions.
- `test_02_invalid_factor_values_outside_range`: Verified rejection of inputs outside $[0.0, 1.0]$.
- `test_03_weight_validation`: Verified strict validation that factor weights sum to 1.0.
- `test_04_priority_band_boundaries`: Verified transitions between Routine, Medium, High, and Critical.
- `test_05_safety_override_independent_of_weighted_score`: Verified automated overrides promote low-score incidents to Critical Review.
- `test_06_missing_and_stale_data_handling`: Verified distinct zero vs missing population and stale weather warnings.
- `test_07_dynamic_time_factor_calculation`: Verified linear time escalation capped at 24 hours.
- `test_08_duplicate_reports_not_inflating_recurrence`: Verified identical cluster reports do not distort recurrence count.
- `test_09_sla_breach_detection`: Verified overdue alerts trigger without altering physical hazard score.
- `test_10_deterministic_ranking_and_tie_breaking`: Verified multi-tier queue sorting and age tie-breaker.
- `test_11_audit_history_persistence`: Verified multiple assessments are appended without overwriting history.
- `test_12_exactly_140_reports_in_simulator`: Verified exact 140 report count (28 school, 36 boundary, 32 bot, 44 routine).
- `test_13_genuine_hazard_preserved_under_coordinated_abuse`: Verified independent emergency remains in Top 2 during bot swarm.
- `test_14_api_validation_and_error_handling`: Verified 200 health, 404 missing, 422 validation, and 403 authorization.

---

## 6. End-to-End Verification Script

Run the automated integration verification script:

```bash
cd C:\Users\vivek\.gemini\antigravity\scratch\impactx-overclock\civic_risk_engine
python verify_e2e.py
```

---

## 7. API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health status, formula version, and active factor weights |
| `POST` | `/incidents` | Create a new incident and calculate initial risk assessment |
| `POST` | `/incidents/{id}/assess` | Calculate or recalculate physical risk score and safety overrides |
| `GET` | `/incidents/{id}/risk` | Retrieve latest assessment output |
| `GET` | `/incidents/{id}` | Complete incident dossier including audit logs and history |
| `GET` | `/incidents/{id}/history` | Retrieve full immutable assessment history |
| `POST` | `/incidents/{id}/override` | Apply an authorized manual safety override (supervisor/duty officer) |
| `GET` | `/priority-queue` | Retrieve deterministically ranked municipal triage queue |
| `GET` | `/config/risk-model` | Inspect active factor weights, priority bands, and safety rules |
| `POST` | `/config/risk-model` | Update weights and priority bands with role authorization |
| `POST` | `/simulation/run-140-reports` | Execute the 140-report synthetic storm stress test |
| `GET` | `/simulation/status` | Retrieve latest simulation metrics and cluster statistics |

---

## 8. Project Directory Structure

```text
civic_risk_engine/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entrypoint, CORS, static mount
│   │   ├── config.py                # Weights, priority bands, hazard taxonomy, safety rules
│   │   ├── core/
│   │   │   ├── risk_scorer.py       # 6-factor deterministic calculation & contributions
│   │   │   ├── feature_extractor.py # Feature extraction, GIS decay, missing data handling
│   │   │   ├── safety_rules.py      # Independent safety override engine
│   │   │   └── priority_engine.py   # Deterministic queue ranking & SLA tracking
│   │   ├── models/
│   │   │   ├── database.py          # SQLAlchemy models (Incident, Assessment, Audit, Report)
│   │   │   └── schemas.py           # Pydantic validation schemas
│   │   ├── services/
│   │   │   ├── incident_service.py  # Incident lifecycle, persistence, audit logging
│   │   │   └── simulation_service.py# 140-report generator & scenario clustering
│   │   └── api/
│   │       ├── incidents.py         # Incident endpoints
│   │       ├── priority.py          # Priority queue endpoint
│   │       ├── config_api.py        # Model configuration endpoints
│   │       └── simulation.py        # Scenario simulator endpoints
│   ├── tests/
│   │   └── test_risk_engine.py      # 14 pytest automated test cases
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
│   │       ├── IncidentDetail.tsx   # Dossier, audit ledger & override form
│   │       └── ScenarioSimulator.tsx# 140-report stress test dashboard
│   ├── dist/                        # Production frontend build
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── verify_e2e.py                    # Complete end-to-end integration verifier
├── .env.example                     # Environment configuration template
└── README.md                        # Documentation & setup guide
```

---
*Built for Team OverClock | IMPACTX 2026 Challenge 10: "Your City, Your Services" | VIT-AP University.*
