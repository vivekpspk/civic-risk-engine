# IMPACTX 2026 — Challenge 10: Your City, Your Services
## Team OverClock | Backend Integration Guide & Lifecycle API Contracts
**Service:** Explainable Civic Risk Scoring, Priority Engine & Complaint Lifecycle Backend  
**Institution:** VIT-AP University  
**Formula Version:** `v1.0.0` (`Risk Score = 100 * (0.25H + 0.20S + 0.20P + 0.15W + 0.10T + 0.10C)`)

---

## 1. System Architecture & Complete Complaint Lifecycle

The backend implements the complete end-to-end municipal issue lifecycle:

$$\text{Citizen Report (Before Photo)} \longrightarrow \text{Automated Risk Assessment} \longrightarrow \text{Admin Assigns Worker} \longrightarrow \text{Worker Repair} \longrightarrow \text{Worker Uploads After Photo} \longrightarrow \text{Admin Verifies Proof} \longrightarrow \text{Citizen Public Tracking & SMS Notification}$$

```
                           [ Citizen Complaint ]
                  (Text, GPS/Address, Before-Photo Evidence)
                                   │
                                   ▼ [SUBMITTED]
 ┌─────────────────────────────────────────────────────────────────┐
 │                   AUTOMATIC FACTOR EXTRACTION                   │
 ├────────────────────────────────┬────────────────────────────────┤
 │ H: 24 Rain Hazards Taxonomy    │ S: Geodesic Sensitive Distance │
 │ P: Population Exposure Model   │ W: Cached Weather / Doppler    │
 │ T: Time Elapsed Escalation     │ C: Distinct Ward Recurrence    │
 └────────────────────────────────┴────────────────────────────────┘
                                   │
                                   ▼ [ASSESSED]
 ┌─────────────────────────────────────────────────────────────────┐
 │               INDEPENDENT SAFETY OVERRIDE ENGINE                │
 │    Forces Imminent Life Hazards to Top of Priority Queue        │
 └─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │                  ADMINISTRATOR PRIORITY QUEUE                   │
 │   Admin views prioritized complaints & assigns field worker     │
 └─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼ [ASSIGNED]
 ┌─────────────────────────────────────────────────────────────────┐
 │                     FIELD WORKER WORKFLOW                       │
 │  1. Worker accepts assignment [ACCEPTED]                        │
 │  2. Worker arrives on site and starts work [IN_PROGRESS]        │
 │  3. Worker uploads after-resolution photos                      │
 │  4. Worker submits resolution report [VERIFICATION_REQUIRED]    │
 │  *(Worker CANNOT mark complaint completed directly)*            │
 └─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼ [VERIFICATION_REQUIRED]
 ┌─────────────────────────────────────────────────────────────────┐
 │             ADMINISTRATOR VERIFICATION & COMPARISON             │
 │  1. Admin inspects side-by-side Before and After photos         │
 │  2. If approved -> [COMPLETED] & triggers citizen SMS           │
 │  3. If rejected -> [IN_PROGRESS] with mandatory reason          │
 │  4. If recurring post-repair -> [REOPENED]                      │
 └─────────────────────────────────────────────────────────────────┘
                                   │
            ┌──────────────────────┴──────────────────────┐
            ▼                                             ▼
 [CITIZEN PUBLIC TRACKING]                      [SMS NOTIFICATION]
 (Before/After Proof, Timeline,                ("Complaint resolved & verified.
  Zero PII Leaked to Public)                    View photos & details at portal.")
```

---

## 2. Complete Lifecycle State Machine (11 Statuses)

| Status | Description | Permitted Next Statuses | Actor Role Authorized |
| :--- | :--- | :--- | :--- |
| `SUBMITTED` | Citizen submitted complaint | `ASSESSED`, `ASSIGNED`, `REJECTED` | Citizen / System |
| `ASSESSED` | Automated risk assessment complete | `ASSIGNED`, `REJECTED` | System / Admin |
| `ASSIGNED` | Admin assigned worker | `ACCEPTED`, `ASSIGNED` (reassign), `REJECTED` | Administrator |
| `ACCEPTED` | Assigned worker accepted task | `IN_PROGRESS`, `UNABLE_TO_RESOLVE`, `ASSIGNED` | Assigned Worker |
| `IN_PROGRESS` | Worker commenced inspection/repairs | `VERIFICATION_REQUIRED`, `UNABLE_TO_RESOLVE` | Assigned Worker |
| `RESOLUTION_SUBMITTED` | Worker submitted completion details | `VERIFICATION_REQUIRED`, `COMPLETED`, `IN_PROGRESS` | Worker / Admin |
| `VERIFICATION_REQUIRED` | Awaiting administrator verification | `COMPLETED` (approved), `IN_PROGRESS` (rejected) | Administrator |
| `COMPLETED` | Resolution verified by administrator | `REOPENED` (if recurring or substandard) | Administrator |
| `REOPENED` | Reopened complaint | `ASSIGNED`, `IN_PROGRESS`, `REJECTED` | Administrator |
| `REJECTED` | Complaint rejected with reason | `REOPENED`, `ASSIGNED` | Administrator |
| `UNABLE_TO_RESOLVE` | Genuine obstacle reported | `ASSIGNED` (reassign), `IN_PROGRESS`, `REJECTED` | Assigned Worker / Admin |

### Strict Security Invariants:
1. **No Worker Self-Approval:** A field worker cannot transition any complaint to `COMPLETED`. Administrator verification is mandatory.
2. **Mandatory Evidence:** A resolution cannot be marked `COMPLETED` without at least one verified after-resolution photo.
3. **No Cross-Worker Tampering:** A worker can only accept, start, or submit resolutions for complaints assigned to their worker ID.
4. **Immutable Audit Ledger:** Every status change is saved to `status_history` and `audit_logs` with timestamps and actor roles.
5. **Resilient Notifications:** SMS notification failures never roll back complaint completion or database state.

---

## 3. API Endpoints & Contract Specifications

### 3.1 Citizen Complaint Intake
**Endpoint:** `POST /api/complaints`  
**Description:** Accepts natural language reports without requiring citizens to calculate risk or rate severity.

#### Request Body (`application/json`):
```json
{
  "description": "Water is accumulating near a school, and an uncovered manhole is visible during heavy rain.",
  "latitude": 16.5063,
  "longitude": 80.6481,
  "location_address": "Near St. Mary's School Gate, Ward 07",
  "hazard_category_hint": "open_manhole",
  "evidence_photos": ["data:image/jpeg;base64,..."],
  "reporter_name": "Anil Rao",
  "reporter_phone": "+91-9876543210",
  "consent_given": true,
  "consent_sms": true
}
```

#### Response Body (`201 Created`):
```json
{
  "complaint_id": "CIV-2026-960ABB34",
  "status": "submitted",
  "hazard_category": "open_manhole",
  "hazard_display_name": "Open or Uncovered Manhole",
  "risk_score": 78.5,
  "priority_band": "Critical",
  "assigned_department": "Drainage & Sewerage Department",
  "assigned_ward": "Ward 07",
  "is_boundary_dispute": false,
  "sla_deadline": "2026-10-24T07:38:29.043Z",
  "estimated_response_window": "Immediate Dispatch (1.0 Hours SLA)",
  "plain_language_explanation": "SAFETY OVERRIDE ACTIVATED: Open manhole in high-proximity zone (<100m) of school triggers mandatory safety override for immediate dispatch. • Nearest facility 'St. Mary's Public School' is 15.2m away.",
  "safety_override_active": true,
  "tracking_url": "/api/public/complaints/CIV-2026-960ABB34"
}
```

---

### 3.2 Evidence Management Endpoints

#### Upload Before Photo (Citizen)
`POST /api/complaints/{complaint_id}/evidence/before` (Multipart file or JSON base64)

#### Upload After Photo (Field Worker)
`POST /api/worker/complaints/{complaint_id}/evidence/after` (Multipart file or JSON base64)
- Requires `X-Worker-ID` header or `worker_id` form field.

#### Side-by-Side Before-and-After Comparison Contract
`GET /api/complaints/{complaint_id}/comparison`
```json
{
  "complaint_id": "CIV-2026-960ABB34",
  "title": "Open or Uncovered Manhole - Ward 07",
  "status": "VERIFICATION_REQUIRED",
  "ward": "Ward 07",
  "before_evidence": [
    {
      "evidence_id": "EVID-7A8B9C0D",
      "evidence_type": "before",
      "original_filename": "citizen_hazard.jpg",
      "mime_type": "image/jpeg",
      "file_size_bytes": 104250,
      "uploaded_by_role": "citizen",
      "uploaded_at": "2026-10-24T06:00:00Z",
      "redaction_status": "approved",
      "view_url": "/api/evidence/EVID-7A8B9C0D/file"
    }
  ],
  "after_evidence": [
    {
      "evidence_id": "EVID-1E2F3A4B",
      "evidence_type": "after",
      "original_filename": "worker_after_repair.jpg",
      "mime_type": "image/jpeg",
      "file_size_bytes": 142080,
      "uploaded_by_role": "worker",
      "uploaded_at": "2026-10-24T07:15:00Z",
      "redaction_status": "approved",
      "view_url": "/api/evidence/EVID-1E2F3A4B/file"
    }
  ],
  "total_before_count": 1,
  "total_after_count": 1,
  "resolution_summary": {
    "worker_id": "WRK-101",
    "description": "Installed heavy-duty reinforced ductile iron cover with locking pins.",
    "action_taken": "Manhole sealed and tested under water accumulation. Hazard eliminated.",
    "verification_status": "pending"
  }
}
```

#### Safe File Retrieval
`GET /api/evidence/{evidence_id}/file`  
Streams clean, EXIF-stripped image bytes with appropriate Content-Type header. Does NOT expose raw disk paths.

---

### 3.3 Field Worker Operations

#### List Assigned Tasks
`GET /api/worker/tasks?worker_id=WRK-101` (or header `X-Worker-ID: WRK-101`)

#### Accept Assignment
`POST /api/worker/tasks/{complaint_id}/accept`
```json
{
  "worker_id": "WRK-101",
  "notes": "Task accepted. En route with repair truck."
}
```

#### Start Work
`POST /api/worker/tasks/{complaint_id}/start`
```json
{
  "worker_id": "WRK-101",
  "inspection_notes": "Arrived on site. Cordoned off area."
}
```

#### Report Blocker (Unable to Resolve)
`POST /api/worker/tasks/{complaint_id}/unable-to-resolve`
```json
{
  "worker_id": "WRK-101",
  "reason": "Requires electricity board power shutoff before drainage pump can be operated."
}
```

#### Submit Resolution
`POST /api/worker/tasks/{complaint_id}/submit-resolution`
```json
{
  "worker_id": "WRK-101",
  "description": "Installed heavy-duty reinforced ductile iron cover with locking pins.",
  "action_taken": "Manhole sealed and tested under water accumulation.",
  "after_evidence_ids": ["EVID-1E2F3A4B"],
  "completion_latitude": 16.5063,
  "completion_longitude": 80.6481
}
```

---

### 3.4 Administrator Verification & Management

#### Assign Worker
`POST /api/admin/complaints/{complaint_id}/assign`
```json
{
  "worker_id": "WRK-101",
  "admin_id": "COMMISSIONER-SHARMA",
  "instructions": "Immediate dispatch: replace damaged lid with ductile iron cover.",
  "target_completion_time": "2026-10-24T08:00:00Z"
}
```

#### Verify Resolution (Approve or Reject)
`POST /api/admin/complaints/{complaint_id}/verify-resolution`
```json
{
  "decision": "approve",
  "admin_id": "COMMISSIONER-SHARMA",
  "notes": "Verified before and after photographic evidence. Work approved as fully resolved."
}
```
*Note: Setting decision to `approve` marks status as `COMPLETED` and dispatches the citizen SMS notification. Setting `reject` returns status to `IN_PROGRESS`.*

#### Reopen Completed Complaint
`POST /api/admin/complaints/{complaint_id}/reopen`
```json
{
  "admin_id": "COMMISSIONER-SHARMA",
  "reason": "Asphalt washed away in morning thunderstorm; needs permanent hot-mix patch."
}
```

#### Reject Complaint
`POST /api/admin/complaints/{complaint_id}/reject`
```json
{
  "admin_id": "COMMISSIONER-SHARMA",
  "reason": "Duplicate ticket: issue already registered and undergoing scheduled maintenance."
}
```

#### List Municipal Workers
`GET /api/admin/workers`

#### Notification History
`GET /api/admin/notifications`

---

### 3.5 Citizen Public Tracking Endpoint

**Endpoint:** `GET /api/public/complaints/{public_complaint_id}`  
**Privacy Guarantee:** Never exposes citizen phone, email, worker contact, or internal admin notes.

```json
{
  "complaint_id": "CIV-2026-960ABB34",
  "status": "COMPLETED",
  "submitted_at": "2026-10-24T06:00:00Z",
  "hazard_category": "Open or Uncovered Manhole",
  "general_description": "Water is accumulating near a school, and an uncovered manhole is visible during heavy rain.",
  "priority_band": "Critical",
  "ward": "Ward 07",
  "is_reopened": false,
  "status_timeline": [
    {"timestamp": "2026-10-24T06:00:00Z", "status": "SUBMITTED", "actor_role": "citizen"},
    {"timestamp": "2026-10-24T06:00:05Z", "status": "ASSESSED", "actor_role": "system"},
    {"timestamp": "2026-10-24T06:15:00Z", "status": "ASSIGNED", "actor_role": "administrator"},
    {"timestamp": "2026-10-24T06:20:00Z", "status": "ACCEPTED", "actor_role": "worker"},
    {"timestamp": "2026-10-24T06:30:00Z", "status": "IN_PROGRESS", "actor_role": "worker"},
    {"timestamp": "2026-10-24T07:15:00Z", "status": "VERIFICATION_REQUIRED", "actor_role": "worker"},
    {"timestamp": "2026-10-24T07:20:00Z", "status": "COMPLETED", "actor_role": "administrator"}
  ],
  "before_photos": [
    {"evidence_id": "EVID-7A8B9C0D", "view_url": "/api/evidence/EVID-7A8B9C0D/file"}
  ],
  "after_photos": [
    {"evidence_id": "EVID-1E2F3A4B", "view_url": "/api/evidence/EVID-1E2F3A4B/file"}
  ],
  "resolution_description": "Installed heavy-duty reinforced ductile iron cover with locking pins.",
  "action_performed": "Manhole sealed and tested under water accumulation. Hazard eliminated.",
  "resolved_at": "2026-10-24T07:20:00Z",
  "tracking_url": "/api/public/complaints/CIV-2026-960ABB34"
}
```

---

## 4. SMS Notification Integration Guide

The backend uses a modular notification provider architecture:
- **Development / Test Mode (Default):** `MockNotificationProvider` automatically simulates SMS delivery, records message bodies and simulated statuses in the database, and clearly reports `mock-sms-provider`. Tests run 100% offline without requiring paid SMS credentials.
- **Production Mode:** Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_PHONE` in `.env`. The backend automatically switches to `ProductionTwilioProvider` and dispatches live SMS.
- **Idempotency Protection:** Each completion SMS generates a unique key `COMPL-RESOLVED-{complaint_id}`. Duplicate calls will return `already_sent` without charging SMS credits.
- **Citizen Consent:** If `consent_sms` is `False`, the notification is logged as `skipped_no_consent` and no SMS is sent.

---

## 5. Automated Verification & Test Commands

Run the complete test suite:
```bash
cd backend
python -m pytest -v
```

Run the end-to-end integration verifier (including the 8-step live lifecycle demonstration):
```bash
python verify_e2e.py
```
