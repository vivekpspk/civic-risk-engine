"""
safety_rules.py
Configurable, explainable safety override engine operating independently
of the mathematical weighted risk formula.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TriggeredSafetyRule(BaseModel):
    rule_id: str
    rule_name: str
    condition_matched: str
    severity_level: str  # "Critical", "High"
    trigger_result: str  # "CRITICAL_REVIEW", "IMMEDIATE_DISPATCH"
    explanation: str
    evidence_status: str
    timestamp: datetime
    rule_version: str


class SafetyOverrideEvaluation(BaseModel):
    active: bool = False
    override_type: str = "none"  # "none", "automated_rule", "manual_authorized"
    effective_severity: Optional[str] = None
    triggered_rules: List[TriggeredSafetyRule] = Field(default_factory=list)
    manual_override: Optional[Dict[str, str]] = None
    summary_explanation: str = "No safety overrides triggered; priority driven by risk score and SLA."


def evaluate_safety_rules(
    hazard_type: str,
    factors: Dict[str, float],
    evidence_status: str = "reported",
    manual_override_data: Optional[Dict[str, str]] = None,
    config=None
) -> SafetyOverrideEvaluation:
    """
    Evaluates safety rules independently of the weighted risk score.
    """
    from app.config import active_config
    cfg = config or active_config

    now = datetime.now(timezone.utc)
    clean_hazard = hazard_type.lower().strip().replace(" ", "_")
    clean_evidence = evidence_status.lower().strip()

    triggered: List[TriggeredSafetyRule] = []

    # 1. Check Automated Configured Safety Rules
    for rule in cfg.safety_rules:
        # Check hazard match
        hazard_match = any(h in clean_hazard or clean_hazard in h for h in rule.hazard_types)
        if not hazard_match:
            continue

        # Check evidence match (we do not automatically dismiss 'reported')
        if clean_evidence not in rule.required_evidence:
            continue

        # Check proximity threshold if required
        if rule.min_proximity is not None:
            prox = factors.get("sensitive_site_proximity", 0.0)
            if prox < rule.min_proximity:
                continue

        # Check weather risk threshold if required
        if rule.min_weather_risk is not None:
            w_risk = factors.get("weather_risk", 0.0)
            if w_risk < rule.min_weather_risk:
                continue

        # Check population threshold if required
        if rule.min_population is not None:
            pop = factors.get("population_exposed", 0.0)
            if pop < rule.min_population:
                continue

        # Rule condition matched!
        triggered.append(
            TriggeredSafetyRule(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                condition_matched=rule.condition_description,
                severity_level=rule.severity_level,
                trigger_result=rule.trigger_result,
                explanation=rule.explanation,
                evidence_status=evidence_status,
                timestamp=now,
                rule_version=rule.version,
            )
        )

    # 2. Check Manual Authorized Override
    if manual_override_data and manual_override_data.get("is_active"):
        authorized_by = manual_override_data.get("authorized_by", "Unknown Official")
        reason = manual_override_data.get("reason", "Administrative emergency intervention")
        role = manual_override_data.get("role", "duty_officer")
        target_severity = manual_override_data.get("severity", "Critical")

        return SafetyOverrideEvaluation(
            active=True,
            override_type="manual_authorized",
            effective_severity=target_severity,
            triggered_rules=triggered,
            manual_override={
                "authorized_by": authorized_by,
                "role": role,
                "reason": reason,
                "target_severity": target_severity,
                "timestamp": now.isoformat(),
            },
            summary_explanation=f"Manual authorized safety override applied by {authorized_by} ({role}): {reason}"
        )

    # If automated rules triggered
    if triggered:
        highest_severity = "Critical" if any(r.severity_level == "Critical" for r in triggered) else "High"
        rule_names = ", ".join(r.rule_name for r in triggered)
        return SafetyOverrideEvaluation(
            active=True,
            override_type="automated_rule",
            effective_severity=highest_severity,
            triggered_rules=triggered,
            summary_explanation=f"Automated safety override triggered by {len(triggered)} rule(s): {rule_names}."
        )

    return SafetyOverrideEvaluation(
        active=False,
        override_type="none",
        effective_severity=None,
        triggered_rules=[],
        summary_explanation="No safety overrides active; prioritizing by physical risk score and SLA urgency."
    )
