"""
priority_engine.py
Dynamic priority ranking, SLA tracking, multi-tier queue sorting,
and deterministic tie-breaking.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.risk_scorer import RiskCalculationResult
from app.core.safety_rules import SafetyOverrideEvaluation


class SLAMonitorResult(BaseModel):
    sla_deadline: Optional[datetime] = None
    sla_status: str = "within_sla"  # "within_sla", "imminent_breach", "breached", "untracked"
    elapsed_minutes: float = 0.0
    remaining_minutes: Optional[float] = None
    is_breached: bool = False
    escalation_alert: Optional[str] = None


def evaluate_sla_status(
    created_at: datetime,
    sla_deadline: Optional[datetime],
    current_time: Optional[datetime] = None
) -> SLAMonitorResult:
    """
    Evaluates SLA status separately from physical risk score.
    Overdue incidents trigger an escalation alert without altering physical hazard severity.
    """
    now = current_time or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    elapsed_mins = max(0.0, (now - created_at).total_seconds() / 60.0)

    if not sla_deadline:
        return SLAMonitorResult(
            sla_deadline=None,
            sla_status="untracked",
            elapsed_minutes=round(elapsed_mins, 1),
            remaining_minutes=None,
            is_breached=False,
            escalation_alert=None,
        )

    if sla_deadline.tzinfo is None:
        sla_deadline = sla_deadline.replace(tzinfo=timezone.utc)

    diff_seconds = (sla_deadline - now).total_seconds()
    remaining_mins = round(diff_seconds / 60.0, 1)

    if diff_seconds < 0:
        overdue_mins = abs(remaining_mins)
        return SLAMonitorResult(
            sla_deadline=sla_deadline,
            sla_status="breached",
            elapsed_minutes=round(elapsed_mins, 1),
            remaining_minutes=remaining_mins,
            is_breached=True,
            escalation_alert=f"SLA BREACHED: Overdue by {overdue_mins:.0f} minutes! Auto-escalated to Duty Officer.",
        )
    elif diff_seconds <= 1800:  # <= 30 minutes remaining
        return SLAMonitorResult(
            sla_deadline=sla_deadline,
            sla_status="imminent_breach",
            elapsed_minutes=round(elapsed_mins, 1),
            remaining_minutes=remaining_mins,
            is_breached=False,
            escalation_alert=f"SLA WARNING: {remaining_mins:.0f} minutes remaining before deadline breach.",
        )

    return SLAMonitorResult(
        sla_deadline=sla_deadline,
        sla_status="within_sla",
        elapsed_minutes=round(elapsed_mins, 1),
        remaining_minutes=remaining_mins,
        is_breached=False,
        escalation_alert=None,
    )


class PriorityQueueItem(BaseModel):
    queue_rank: int = 1
    incident_id: str
    hazard_type: str
    risk_score: float
    effective_priority_band: str
    safety_override_active: bool
    safety_override_reason: Optional[str] = None
    sla_status: str
    sla_deadline: Optional[datetime] = None
    is_sla_breached: bool = False
    evidence_status: str
    assigned_department: Optional[str] = None
    created_at: datetime
    elapsed_minutes: float
    factor_contributions: Dict[str, float]
    uncertainty_warnings: List[str]
    ranking_explanation: str
    recommended_action: str


def rank_priority_queue(
    assessments: List[Dict[str, Any]],
    current_time: Optional[datetime] = None
) -> List[PriorityQueueItem]:
    """
    Ranks incidents deterministically using a multi-tier hierarchy:
    1. Active Safety Override (Critical review takes absolute precedence)
    2. Physical Risk Score (Descending)
    3. SLA Urgency (Breached > Imminent > Within SLA)
    4. Incident Age / Created At (Older first as documented tie-breaker)
    """
    now = current_time or datetime.now(timezone.utc)

    # Sort key tuple
    def sort_key(item: Dict[str, Any]):
        override: SafetyOverrideEvaluation = item["safety_override"]
        risk_res: RiskCalculationResult = item["risk_result"]
        sla_res: SLAMonitorResult = item["sla_result"]
        created: datetime = item["created_at"]

        # 1. Override rank (1 if active, 0 otherwise)
        override_weight = 1 if override.active else 0
        override_sev = 2 if override.effective_severity == "Critical" else (1 if override.active else 0)

        # 2. SLA urgency weight: breached = 3, imminent = 2, within = 1, untracked = 0
        sla_weight = 0
        if sla_res.sla_status == "breached":
            sla_weight = 3
        elif sla_res.sla_status == "imminent_breach":
            sla_weight = 2
        elif sla_res.sla_status == "within_sla":
            sla_weight = 1

        # 3. Risk score float
        score = risk_res.rounded_score

        # 4. Age timestamp in epoch (older has smaller timestamp, so negative timestamp for older first)
        t_epoch = created.timestamp() if created else 0.0

        # We want descending order for override, score, sla_weight, and ascending order for created_at (older first)
        return (
            override_sev,
            score,
            sla_weight,
            -t_epoch
        )

    sorted_items = sorted(assessments, key=sort_key, reverse=True)

    ranked_queue: List[PriorityQueueItem] = []
    for rank, it in enumerate(sorted_items, start=1):
        override: SafetyOverrideEvaluation = it["safety_override"]
        risk_res: RiskCalculationResult = it["risk_result"]
        sla_res: SLAMonitorResult = it["sla_result"]
        created: datetime = it["created_at"]

        effective_band = override.effective_severity if override.active else risk_res.priority_band

        # Formulate recommended action
        if override.active:
            recommended = "IMMEDIATE EMERGENCY DISPATCH: Safety rule override active. Deploy emergency field crew immediately."
            ranking_exp = f"Ranked #{rank} due to active {override.effective_severity} Safety Override: {override.summary_explanation}"
        elif sla_res.is_breached:
            recommended = "URGENT ESCALATION: SLA deadline breached. Escalate to Ward Supervisor for expedited response."
            ranking_exp = f"Ranked #{rank} with Risk Score {risk_res.rounded_score}/100 and SLA breach alert."
        elif effective_band == "Critical":
            recommended = "High-priority immediate response within 30 minutes."
            ranking_exp = f"Ranked #{rank} based on Critical physical risk score ({risk_res.rounded_score}/100)."
        elif effective_band == "High":
            recommended = "Prioritize inspection and repair within 2 hours."
            ranking_exp = f"Ranked #{rank} based on High physical risk score ({risk_res.rounded_score}/100)."
        elif effective_band == "Medium":
            recommended = "Schedule for standard maintenance shift within 24 hours."
            ranking_exp = f"Ranked #{rank} based on Medium risk score ({risk_res.rounded_score}/100)."
        else:
            recommended = "Routine backlog intake; inspect within 72 hours."
            ranking_exp = f"Ranked #{rank} based on Routine risk score ({risk_res.rounded_score}/100)."

        ranked_queue.append(
            PriorityQueueItem(
                queue_rank=rank,
                incident_id=it["incident_id"],
                hazard_type=it["hazard_type"],
                risk_score=risk_res.rounded_score,
                effective_priority_band=effective_band,
                safety_override_active=override.active,
                safety_override_reason=override.summary_explanation if override.active else None,
                sla_status=sla_res.sla_status,
                sla_deadline=sla_res.sla_deadline,
                is_sla_breached=sla_res.is_breached,
                evidence_status=it.get("evidence_status", "reported"),
                assigned_department=it.get("assigned_department", "Unassigned"),
                created_at=created,
                elapsed_minutes=sla_res.elapsed_minutes,
                factor_contributions=risk_res.factor_contributions,
                uncertainty_warnings=it.get("uncertainty_warnings", []),
                ranking_explanation=ranking_exp,
                recommended_action=recommended,
            )
        )

    return ranked_queue
