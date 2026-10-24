"""
notification_service.py
SMS Notification Service & Provider Architecture for Civic Complaint Lifecycle.
Supports Mock SMS Provider (for offline development and pytest tests)
and Production SMS Provider (Twilio/HTTP SMS API via environment configuration).
Includes idempotency keys to prevent duplicate completion notifications,
consent enforcement, and graceful fault tolerance.
"""

import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import NotificationModel, IncidentModel, AuditLogModel


class NotificationResult(BaseModel):
    success: bool
    status: str  # "sent", "simulated", "failed", "skipped_no_consent", "skipped_no_phone", "already_sent"
    provider: str
    message_id: Optional[str] = None
    recipient_phone: Optional[str] = None
    error_message: Optional[str] = None


class BaseNotificationProvider(ABC):
    @abstractmethod
    def send_sms(self, phone_number: str, message: str, idempotency_key: str) -> NotificationResult:
        """Sends an SMS message and returns delivery status."""
        pass


class MockNotificationProvider(BaseNotificationProvider):
    """
    Mock SMS provider for local testing and automated verification.
    Records delivery in memory and database with simulated flag.
    """
    def __init__(self):
        self.sent_messages: List[Dict[str, any]] = []

    def send_sms(self, phone_number: str, message: str, idempotency_key: str) -> NotificationResult:
        msg_id = f"MOCK-SMS-{uuid.uuid4().hex[:10].upper()}"
        record = {
            "message_id": msg_id,
            "phone_number": phone_number,
            "message": message,
            "idempotency_key": idempotency_key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "simulated"
        }
        self.sent_messages.append(record)
        return NotificationResult(
            success=True,
            status="simulated",
            provider="mock-sms-provider",
            message_id=msg_id,
            recipient_phone=phone_number
        )


class ProductionTwilioProvider(BaseNotificationProvider):
    """
    Production SMS provider using Twilio or standard REST SMS gateway.
    Activates when TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are present in .env.
    """
    def __init__(self, account_sid: str, auth_token: str, from_phone: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_phone = from_phone

    def send_sms(self, phone_number: str, message: str, idempotency_key: str) -> NotificationResult:
        try:
            import urllib.request
            import urllib.parse
            import base64

            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            data = urllib.parse.urlencode({
                "To": phone_number,
                "From": self.from_phone,
                "Body": message
            }).encode("utf-8")

            req = urllib.request.Request(url, data=data, method="POST")
            auth_str = f"{self.account_sid}:{self.auth_token}"
            auth_b64 = base64.b64encode(auth_str.encode("ascii")).decode("ascii")
            req.add_header("Authorization", f"Basic {auth_b64}")

            with urllib.request.urlopen(req, timeout=10) as resp:
                res_body = resp.read().decode("utf-8")
                return NotificationResult(
                    success=True,
                    status="sent",
                    provider="twilio",
                    message_id=f"TWILIO-{uuid.uuid4().hex[:10].upper()}",
                    recipient_phone=phone_number
                )
        except Exception as e:
            return NotificationResult(
                success=False,
                status="failed",
                provider="twilio",
                recipient_phone=phone_number,
                error_message=str(e)
            )


# Initialize provider based on environment configuration
def get_configured_provider() -> BaseNotificationProvider:
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_phone = os.environ.get("TWILIO_FROM_PHONE")

    if account_sid and auth_token and from_phone:
        return ProductionTwilioProvider(account_sid, auth_token, from_phone)
    return MockNotificationProvider()


active_sms_provider: BaseNotificationProvider = get_configured_provider()


class NotificationService:
    @staticmethod
    def send_resolution_completion_sms(
        db: Session,
        complaint_id: str,
        force_retry: bool = False
    ) -> NotificationResult:
        """
        Sends an SMS notification to the citizen when their complaint is verified as COMPLETED.
        Enforces idempotency, consent check, and ensures notification failure never rolls back DB.
        """
        complaint = db.query(IncidentModel).filter(IncidentModel.incident_id == complaint_id).first()
        if not complaint:
            return NotificationResult(
                success=False,
                status="failed",
                provider="none",
                error_message=f"Complaint '{complaint_id}' not found."
            )

        # 1. Consent Check
        # Check both consent_sms and legacy consent_given
        has_consent = getattr(complaint, "consent_sms", True) and getattr(complaint, "consent_given", True)
        if not has_consent:
            # Log skipped attempt
            record = NotificationModel(
                complaint_id=complaint_id,
                recipient_phone=complaint.reporter_phone or "UNKNOWN",
                message="[SKIPPED: Citizen did not provide consent for SMS notifications]",
                provider=active_sms_provider.__class__.__name__,
                status="skipped_no_consent",
                idempotency_key=f"COMPL-{complaint_id}-NO-CONSENT",
                attempts=1,
                error_message="User did not consent to SMS updates",
                sent_at=datetime.now(timezone.utc)
            )
            db.add(record)
            db.commit()
            return NotificationResult(
                success=True,
                status="skipped_no_consent",
                provider="none",
                recipient_phone=complaint.reporter_phone,
                error_message="Citizen has not opted into SMS notifications."
            )

        # 2. Phone Check
        phone = complaint.reporter_phone
        if not phone or not phone.strip():
            record = NotificationModel(
                complaint_id=complaint_id,
                recipient_phone="NONE",
                message="[SKIPPED: No mobile phone number provided]",
                provider=active_sms_provider.__class__.__name__,
                status="skipped_no_phone",
                idempotency_key=f"COMPL-{complaint_id}-NO-PHONE",
                attempts=1,
                error_message="No phone number provided during submission",
                sent_at=datetime.now(timezone.utc)
            )
            db.add(record)
            db.commit()
            return NotificationResult(
                success=True,
                status="skipped_no_phone",
                provider="none",
                error_message="No phone number on record."
            )

        # 3. Idempotency Check
        idempotency_key = f"COMPL-RESOLVED-{complaint_id}"
        existing = (
            db.query(NotificationModel)
            .filter(NotificationModel.idempotency_key == idempotency_key)
            .first()
        )
        if existing and existing.status in {"sent", "simulated"} and not force_retry:
            return NotificationResult(
                success=True,
                status="already_sent",
                provider=existing.provider,
                message_id=f"EXISTING-{existing.id}",
                recipient_phone=phone,
                error_message="Notification already delivered for this resolution event."
            )

        # 4. Construct Official Notification Message
        message_body = (
            f"Your civic complaint {complaint_id} has been resolved and verified. "
            f"You can view the before-and-after photos and resolution details using the official complaint tracking page."
        )

        # 5. Dispatch SMS via active provider
        try:
            result = active_sms_provider.send_sms(
                phone_number=phone,
                message=message_body,
                idempotency_key=idempotency_key
            )
        except Exception as ex:
            result = NotificationResult(
                success=False,
                status="failed",
                provider=active_sms_provider.__class__.__name__,
                recipient_phone=phone,
                error_message=str(ex)
            )

        # 6. Record Notification Log in Database
        notif_record = NotificationModel(
            complaint_id=complaint_id,
            recipient_phone=phone,
            message=message_body,
            provider=result.provider,
            status=result.status,
            idempotency_key=idempotency_key,
            attempts=1 if not existing else existing.attempts + 1,
            error_message=result.error_message,
            sent_at=datetime.now(timezone.utc)
        )
        db.add(notif_record)

        # 7. Audit Log
        audit = AuditLogModel(
            incident_id=complaint_id,
            action_type=f"NOTIFICATION_{result.status.upper()}",
            details={
                "phone": f"***{phone[-4:]}" if len(phone) >= 4 else "***",
                "status": result.status,
                "provider": result.provider,
                "message_id": result.message_id
            },
            actor="SYSTEM_NOTIFICATION_SERVICE",
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit)
        db.commit()

        return result

    @staticmethod
    def list_notifications(db: Session, limit: int = 50) -> List[Dict[str, any]]:
        records = (
            db.query(NotificationModel)
            .order_by(NotificationModel.sent_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "complaint_id": r.complaint_id,
                "recipient_phone": f"***{r.recipient_phone[-4:]}" if len(r.recipient_phone) >= 4 else r.recipient_phone,
                "message": r.message,
                "provider": r.provider,
                "status": r.status,
                "idempotency_key": r.idempotency_key,
                "attempts": r.attempts,
                "sent_at": r.sent_at.isoformat() if r.sent_at else "",
                "error_message": r.error_message
            }
            for r in records
        ]
