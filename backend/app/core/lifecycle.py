"""
lifecycle.py
Complaint Lifecycle State Machine & Transition Validator for IMPACTX 2026.
Defines the 11 strict lifecycle statuses, validates role-based permissions,
prevents unauthorized transitions, and maintains immutable status history.
"""

from enum import Enum
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.models.database import IncidentModel, StatusHistoryModel, AuditLogModel


class ComplaintLifecycleStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    ASSESSED = "ASSESSED"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLUTION_SUBMITTED = "RESOLUTION_SUBMITTED"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"
    COMPLETED = "COMPLETED"
    REOPENED = "REOPENED"
    REJECTED = "REJECTED"
    UNABLE_TO_RESOLVE = "UNABLE_TO_RESOLVE"


# Permitted state transitions
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    ComplaintLifecycleStatus.SUBMITTED.value: {
        ComplaintLifecycleStatus.ASSESSED.value,
        ComplaintLifecycleStatus.ASSIGNED.value,
        ComplaintLifecycleStatus.REJECTED.value,
    },
    ComplaintLifecycleStatus.ASSESSED.value: {
        ComplaintLifecycleStatus.ASSIGNED.value,
        ComplaintLifecycleStatus.REJECTED.value,
    },
    ComplaintLifecycleStatus.ASSIGNED.value: {
        ComplaintLifecycleStatus.ACCEPTED.value,
        ComplaintLifecycleStatus.ASSIGNED.value,  # Reassignment
        ComplaintLifecycleStatus.REJECTED.value,
    },
    ComplaintLifecycleStatus.ACCEPTED.value: {
        ComplaintLifecycleStatus.IN_PROGRESS.value,
        ComplaintLifecycleStatus.UNABLE_TO_RESOLVE.value,
        ComplaintLifecycleStatus.ASSIGNED.value,  # Reassignment by admin
    },
    ComplaintLifecycleStatus.IN_PROGRESS.value: {
        ComplaintLifecycleStatus.RESOLUTION_SUBMITTED.value,
        ComplaintLifecycleStatus.VERIFICATION_REQUIRED.value,
        ComplaintLifecycleStatus.UNABLE_TO_RESOLVE.value,
        ComplaintLifecycleStatus.ASSIGNED.value,  # Reassignment by admin
    },
    ComplaintLifecycleStatus.RESOLUTION_SUBMITTED.value: {
        ComplaintLifecycleStatus.VERIFICATION_REQUIRED.value,
        ComplaintLifecycleStatus.COMPLETED.value,      # Administrator verification
        ComplaintLifecycleStatus.IN_PROGRESS.value,    # Administrator rejection of resolution
        ComplaintLifecycleStatus.ASSIGNED.value,       # Administrator reassignment
    },
    ComplaintLifecycleStatus.VERIFICATION_REQUIRED.value: {
        ComplaintLifecycleStatus.COMPLETED.value,      # Administrator verification
        ComplaintLifecycleStatus.IN_PROGRESS.value,    # Administrator rejection of resolution
        ComplaintLifecycleStatus.ASSIGNED.value,       # Administrator reassignment
    },
    ComplaintLifecycleStatus.COMPLETED.value: {
        ComplaintLifecycleStatus.REOPENED.value,       # Reopened by admin or citizen escalation
    },
    ComplaintLifecycleStatus.REOPENED.value: {
        ComplaintLifecycleStatus.ASSIGNED.value,
        ComplaintLifecycleStatus.IN_PROGRESS.value,
        ComplaintLifecycleStatus.REJECTED.value,
    },
    ComplaintLifecycleStatus.UNABLE_TO_RESOLVE.value: {
        ComplaintLifecycleStatus.ASSIGNED.value,       # Reassigned to specialist team
        ComplaintLifecycleStatus.IN_PROGRESS.value,
        ComplaintLifecycleStatus.REJECTED.value,
    },
    ComplaintLifecycleStatus.REJECTED.value: {
        ComplaintLifecycleStatus.REOPENED.value,       # Admin reversal of rejection
        ComplaintLifecycleStatus.ASSIGNED.value,
    },
}


def normalize_status(status_str: Optional[str]) -> str:
    """Normalizes any status string into canonical uppercase enum value."""
    if not status_str:
        return ComplaintLifecycleStatus.SUBMITTED.value
    clean = status_str.strip().upper()
    try:
        return ComplaintLifecycleStatus(clean).value
    except ValueError:
        # Backward compatibility for legacy status names
        legacy_map = {
            "SUBMITTED": ComplaintLifecycleStatus.SUBMITTED.value,
            "VERIFIED": ComplaintLifecycleStatus.ASSESSED.value,
            "ASSIGNED": ComplaintLifecycleStatus.ASSIGNED.value,
            "IN_PROGRESS": ComplaintLifecycleStatus.IN_PROGRESS.value,
            "RESOLVED": ComplaintLifecycleStatus.COMPLETED.value,
            "COMPLETED": ComplaintLifecycleStatus.COMPLETED.value,
        }
        return legacy_map.get(clean, clean)


def validate_transition(
    current_status: str,
    target_status: str,
    actor_role: str,
    has_after_evidence: bool = False,
    is_assigned_worker: bool = False,
    is_admin: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Validates state machine rules and actor role permissions.
    Returns (is_valid, error_message).
    """
    curr = normalize_status(current_status)
    tgt = normalize_status(target_status)

    # 1. Immediate role security barriers
    if actor_role == "worker":
        # Workers cannot mark complaints completed under any circumstance
        if tgt == ComplaintLifecycleStatus.COMPLETED.value:
            return False, "Workers cannot approve or mark complaints as COMPLETED. Administrator verification is required."

        # Workers cannot reassign, reopen, or reject
        if tgt in {ComplaintLifecycleStatus.ASSIGNED.value, ComplaintLifecycleStatus.REOPENED.value, ComplaintLifecycleStatus.REJECTED.value}:
            return False, f"Workers cannot transition complaints to '{tgt}'."

    elif actor_role == "citizen":
        return False, "Citizens cannot directly alter administrative workflow status."

    # 2. Check transition graph
    allowed_next = VALID_TRANSITIONS.get(curr, set())
    if tgt not in allowed_next:
        return False, f"Illegal status transition: cannot transition from '{curr}' to '{tgt}'."

    # 3. Worker task assignment check
    if actor_role == "worker":
        # Worker can only modify tasks assigned to them
        if not is_assigned_worker:
            return False, "Worker is not authorized to modify a task assigned to another worker or unassigned."

        # Submitting resolution requires after-evidence
        if tgt in {ComplaintLifecycleStatus.RESOLUTION_SUBMITTED.value, ComplaintLifecycleStatus.VERIFICATION_REQUIRED.value}:
            if not has_after_evidence:
                return False, "Resolution submission requires at least one after-photo evidence upload."

    # 4. Administrator / Supervisor permissions
    elif actor_role in {"administrator", "supervisor", "admin", "municipal_commissioner"}:
        # Admin completing work requires verification evidence unless explicit exception
        if tgt == ComplaintLifecycleStatus.COMPLETED.value:
            if not has_after_evidence:
                return False, "Cannot verify resolution as COMPLETED without after-resolution evidence photos."

    else:
        return False, f"Unknown actor role: '{actor_role}'."

    return True, None


def record_status_history(
    db: Session,
    complaint_id: str,
    previous_status: Optional[str],
    new_status: str,
    actor_id: str,
    actor_role: str,
    notes: Optional[str] = None
) -> StatusHistoryModel:
    """
    Appends an immutable event to the status history and audit ledger.
    """
    history_record = StatusHistoryModel(
        complaint_id=complaint_id,
        previous_status=normalize_status(previous_status) if previous_status else None,
        new_status=normalize_status(new_status),
        actor_id=actor_id,
        actor_role=actor_role,
        timestamp=datetime.now(timezone.utc),
        notes=notes
    )
    db.add(history_record)

    # Also log to tamper-evident audit ledger
    audit_entry = AuditLogModel(
        incident_id=complaint_id,
        action_type=f"STATUS_TRANSITION_{normalize_status(new_status)}",
        details={
            "previous_status": normalize_status(previous_status) if previous_status else None,
            "new_status": normalize_status(new_status),
            "actor_id": actor_id,
            "actor_role": actor_role,
            "notes": notes
        },
        actor=f"{actor_role}:{actor_id}",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit_entry)
    db.flush()
    return history_record
