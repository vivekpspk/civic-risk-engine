"""
database.py
SQLAlchemy database setup and persistent models for Incidents, Assessments,
Safety Overrides, Reports, and Tamper-evident Audit Events.
Designed for SQLite with smooth migration capability to PostgreSQL.
"""

import os
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text, JSON, ForeignKey, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DEFAULT_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "civic_risk.db"))
DB_PATH = os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class IncidentModel(Base):
    __tablename__ = "incidents"

    incident_id = Column(String(64), primary_key=True, index=True)
    hazard_type = Column(String(64), nullable=False, index=True)
    title = Column(String(256), nullable=True)
    description = Column(Text, nullable=True)
    ward = Column(String(32), nullable=True, default="Ward 07")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    evidence_status = Column(String(32), default="reported", nullable=False)  # reported, corroborated, officially_verified
    sla_deadline = Column(DateTime, nullable=True)
    assigned_department = Column(String(64), default="Unassigned", nullable=False)
    cluster_id = Column(String(64), nullable=True, index=True)

    # Citizen complaint & routing extensions
    reporter_name = Column(String(128), nullable=True)  # Privacy protected
    reporter_phone = Column(String(32), nullable=True)  # Privacy protected
    reporter_email = Column(String(128), nullable=True) # Privacy protected
    location_address = Column(String(256), nullable=True)
    category_hint = Column(String(64), nullable=True)
    evidence_urls = Column(JSON, nullable=True)
    consent_given = Column(Boolean, default=True, nullable=False)
    boundary_dispute = Column(Boolean, default=False, nullable=False)
    disputed_wards = Column(JSON, nullable=True)
    status = Column(String(32), default="submitted", nullable=False)  # submitted, verified, assigned, in_progress, resolved
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Gemini AI Triage & Analysis extensions
    ai_reasoning_summary = Column(Text, nullable=True)
    ai_model_used = Column(String(64), nullable=True)
    ai_analysis_status = Column(String(32), default="pending", nullable=True)
    ai_detected_hazard = Column(String(64), nullable=True)
    ai_confidence_score = Column(Float, nullable=True)

    # Worker & Lifecycle tracking extensions
    current_worker_id = Column(String(64), nullable=True, index=True)
    consent_sms = Column(Boolean, default=True, nullable=False)
    reopened_count = Column(Integer, default=0, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    blocker_reason = Column(Text, nullable=True)

    # Relationships
    assessments = relationship("AssessmentModel", back_populates="incident", cascade="all, delete-orphan", order_by="desc(AssessmentModel.assessed_at)")
    audit_logs = relationship("AuditLogModel", back_populates="incident", cascade="all, delete-orphan", order_by="desc(AuditLogModel.timestamp)")
    manual_overrides = relationship("ManualOverrideModel", back_populates="incident", cascade="all, delete-orphan")
    evidence_records = relationship("EvidenceModel", back_populates="incident", cascade="all, delete-orphan", order_by="asc(EvidenceModel.uploaded_at)")
    assignments = relationship("AssignmentModel", back_populates="incident", cascade="all, delete-orphan", order_by="desc(AssignmentModel.assigned_at)")
    resolutions = relationship("ResolutionSubmissionModel", back_populates="incident", cascade="all, delete-orphan", order_by="desc(ResolutionSubmissionModel.submitted_at)")
    status_history_records = relationship("StatusHistoryModel", back_populates="incident", cascade="all, delete-orphan", order_by="asc(StatusHistoryModel.timestamp)")
    notifications = relationship("NotificationModel", back_populates="incident", cascade="all, delete-orphan", order_by="desc(NotificationModel.sent_at)")


# Alias for unified complaint/incident architecture
ComplaintModel = IncidentModel


class AssessmentModel(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    assessed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    risk_score = Column(Float, nullable=False)
    priority_band = Column(String(32), nullable=False)
    formula_version = Column(String(32), default="v1.0.0", nullable=False)
    factor_values = Column(JSON, nullable=False)  # {"hazard_severity": 1.0, ...}
    factor_contributions = Column(JSON, nullable=False)  # {"hazard_severity": 25.0, ...}
    factor_sources = Column(JSON, nullable=True)
    uncertainty_flags = Column(JSON, nullable=False)
    safety_override = Column(JSON, nullable=False)
    sla_status = Column(String(32), nullable=False)
    recommended_action = Column(Text, nullable=False)
    explanations = Column(JSON, nullable=False)

    incident = relationship("IncidentModel", back_populates="assessments")


class ManualOverrideModel(Base):
    __tablename__ = "manual_overrides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    authorized_by = Column(String(128), nullable=False)
    role = Column(String(64), nullable=False)  # "supervisor", "duty_officer", "admin"
    reason = Column(Text, nullable=False)
    target_severity = Column(String(32), default="Critical", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    incident = relationship("IncidentModel", back_populates="manual_overrides")


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=True, index=True)
    action_type = Column(String(64), nullable=False)  # INCIDENT_CREATED, RISK_ASSESSED, OVERRIDE_APPLIED, SLA_ESCALATED
    details = Column(JSON, nullable=False)
    actor = Column(String(128), default="SYSTEM", nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    incident = relationship("IncidentModel", back_populates="audit_logs")


class ReportModel(Base):
    __tablename__ = "reports"

    report_id = Column(String(64), primary_key=True, index=True)
    incident_id = Column(String(64), nullable=True, index=True)
    cluster_id = Column(String(64), nullable=True, index=True)
    reporter_token = Column(String(64), nullable=False)
    hazard_type = Column(String(64), nullable=False)
    raw_text = Column(Text, nullable=False)
    ward = Column(String(32), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_flagged_abuse = Column(Boolean, default=False, nullable=False)
    abuse_reason = Column(String(128), nullable=True)


class EvidenceModel(Base):
    __tablename__ = "evidence"

    evidence_id = Column(String(64), primary_key=True, index=True)
    complaint_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    evidence_type = Column(String(32), nullable=False)  # "before" or "after"
    file_path = Column(String(512), nullable=False)
    original_filename = Column(String(256), nullable=False)
    mime_type = Column(String(64), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    uploaded_by_role = Column(String(32), nullable=False)  # "citizen", "worker", "administrator"
    uploaded_by_id = Column(String(64), nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    redaction_status = Column(String(32), default="approved", nullable=False)  # "approved", "redacted", "awaiting_review"
    sha256_hash = Column(String(64), nullable=True)
    caption = Column(String(256), nullable=True)

    incident = relationship("IncidentModel", back_populates="evidence_records")


class WorkerModel(Base):
    __tablename__ = "workers"

    worker_id = Column(String(64), primary_key=True, index=True)  # e.g. WRK-101
    name = Column(String(128), nullable=False)
    phone = Column(String(32), nullable=False)
    department = Column(String(64), nullable=False)
    ward = Column(String(32), nullable=False)
    status = Column(String(32), default="available", nullable=False)  # "available", "assigned", "on_leave"
    active_tasks_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    assignments = relationship("AssignmentModel", back_populates="worker")


class AssignmentModel(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    worker_id = Column(String(64), ForeignKey("workers.worker_id"), nullable=False, index=True)
    assigned_by_admin = Column(String(128), nullable=False)
    assigned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    instructions = Column(Text, nullable=True)
    target_completion_time = Column(DateTime, nullable=True)
    status = Column(String(32), default="assigned", nullable=False)  # "assigned", "accepted", "in_progress", "completed", "reopened", "cancelled"

    incident = relationship("IncidentModel", back_populates="assignments")
    worker = relationship("WorkerModel", back_populates="assignments")


class ResolutionSubmissionModel(Base):
    __tablename__ = "resolution_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    worker_id = Column(String(64), ForeignKey("workers.worker_id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    action_taken = Column(Text, nullable=False)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completion_latitude = Column(Float, nullable=True)
    completion_longitude = Column(Float, nullable=True)
    blockers = Column(Text, nullable=True)
    after_evidence_ids = Column(JSON, nullable=False)  # list of evidence_ids
    verification_status = Column(String(32), default="pending", nullable=False)  # "pending", "verified", "rejected"
    verified_by_admin = Column(String(128), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)

    incident = relationship("IncidentModel", back_populates="resolutions")


class StatusHistoryModel(Base):
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    previous_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=False)
    actor_id = Column(String(128), nullable=False)
    actor_role = Column(String(32), nullable=False)  # "citizen", "system", "worker", "administrator"
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    notes = Column(Text, nullable=True)

    incident = relationship("IncidentModel", back_populates="status_history_records")


class NotificationModel(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    recipient_phone = Column(String(32), nullable=False)
    message = Column(Text, nullable=False)
    provider = Column(String(64), default="mock", nullable=False)
    status = Column(String(32), default="sent", nullable=False)  # "sent", "simulated", "failed", "skipped_no_consent"
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    attempts = Column(Integer, default=1, nullable=False)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    incident = relationship("IncidentModel", back_populates="notifications")


def init_db(target_engine=None):
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)

    # Auto-migrate missing columns for SQLite
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(eng)
        columns = [c["name"] for c in inspector.get_columns("incidents")]
        new_cols = {
            "reporter_name": "VARCHAR(128)",
            "reporter_phone": "VARCHAR(32)",
            "reporter_email": "VARCHAR(128)",
            "location_address": "VARCHAR(256)",
            "category_hint": "VARCHAR(64)",
            "evidence_urls": "JSON",
            "consent_given": "BOOLEAN DEFAULT 1",
            "boundary_dispute": "BOOLEAN DEFAULT 0",
            "disputed_wards": "JSON",
            "status": "VARCHAR(32) DEFAULT 'submitted'",
            "resolution_notes": "TEXT",
            "resolved_at": "DATETIME",
            "ai_reasoning_summary": "TEXT",
            "ai_model_used": "VARCHAR(64)",
            "ai_analysis_status": "VARCHAR(32) DEFAULT 'pending'",
            "ai_detected_hazard": "VARCHAR(64)",
            "ai_confidence_score": "FLOAT",
            "current_worker_id": "VARCHAR(64)",
            "consent_sms": "BOOLEAN DEFAULT 1",
            "reopened_count": "INTEGER DEFAULT 0",
            "rejection_reason": "TEXT",
            "blocker_reason": "TEXT",
        }
        with eng.connect() as conn:
            for col, col_type in new_cols.items():
                if col not in columns:
                    conn.execute(text(f"ALTER TABLE incidents ADD COLUMN {col} {col_type}"))
            conn.commit()
    except Exception:
        pass

    # Seed default municipal workers if none exist
    try:
        session = sessionmaker(bind=eng)()
        worker_count = session.query(WorkerModel).count()
        if worker_count == 0:
            default_workers = [
                WorkerModel(
                    worker_id="WRK-101",
                    name="Ramesh Kumar",
                    phone="+919876543210",
                    department="Stormwater Drainage & Flood Control",
                    ward="Ward 07",
                    status="available",
                    active_tasks_count=0
                ),
                WorkerModel(
                    worker_id="WRK-102",
                    name="Priya Sharma",
                    phone="+919876543211",
                    department="Roads & Infrastructure Maintenance",
                    ward="Ward 03",
                    status="available",
                    active_tasks_count=0
                ),
                WorkerModel(
                    worker_id="WRK-103",
                    name="Suresh Reddy",
                    phone="+919876543212",
                    department="Electrical & Public Safety",
                    ward="Ward 12",
                    status="available",
                    active_tasks_count=0
                ),
                WorkerModel(
                    worker_id="WRK-104",
                    name="Ananya Das",
                    phone="+919876543213",
                    department="Water Supply & Sewerage Board",
                    ward="Ward 07",
                    status="available",
                    active_tasks_count=0
                ),
            ]
            session.add_all(default_workers)
            session.commit()
        session.close()
    except Exception:
        pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
