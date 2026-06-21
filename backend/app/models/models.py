from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, Enum, JSON, BigInteger, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgres import Base
import enum
import uuid


def gen_uuid():
    return str(uuid.uuid4())


# ── Enums ─────────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    CITIZEN = "citizen"
    INVESTIGATOR = "investigator"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class ComplaintStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INVESTIGATING = "investigating"
    LINKED = "linked"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ComplaintCategory(str, enum.Enum):
    FINANCIAL_FRAUD = "financial_fraud"
    PHISHING = "phishing"
    IDENTITY_THEFT = "identity_theft"
    CYBERBULLYING = "cyberbullying"
    RANSOMWARE = "ransomware"
    HACKING = "hacking"
    SOCIAL_MEDIA_FRAUD = "social_media_fraud"
    UPI_FRAUD = "upi_fraud"
    OTP_FRAUD = "otp_fraud"
    INVESTMENT_FRAUD = "investment_fraud"
    OTHER = "other"


class EntityType(str, enum.Enum):
    PHONE_NUMBER = "phone_number"
    EMAIL = "email"
    URL = "url"
    IP_ADDRESS = "ip_address"
    UPI_ID = "upi_id"
    BANK_ACCOUNT = "bank_account"
    SOCIAL_HANDLE = "social_handle"
    DOMAIN = "domain"
    IFSC_CODE = "ifsc_code"
    KEYWORD = "keyword"


class EvidenceType(str, enum.Enum):
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    OTHER = "other"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Models ────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CITIZEN, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    badge_number = Column(String(50), nullable=True)          # For investigators
    department = Column(String(255), nullable=True)
    preferred_language = Column(String(10), default="en")
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    complaints = relationship("Complaint", back_populates="submitted_by", foreign_keys="Complaint.submitted_by_id")
    assigned_cases = relationship("Complaint", back_populates="assigned_to", foreign_keys="Complaint.assigned_to_id")
    audit_logs = relationship("AuditLog", back_populates="user")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(String, primary_key=True, default=gen_uuid)
    complaint_number = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Enum(ComplaintCategory), nullable=False)
    status = Column(Enum(ComplaintStatus), default=ComplaintStatus.SUBMITTED, index=True)

    # Victim information
    victim_name = Column(String(255), nullable=True)
    victim_phone = Column(String(20), nullable=True)
    victim_email = Column(String(255), nullable=True)
    victim_address = Column(Text, nullable=True)
    financial_loss = Column(Float, nullable=True)
    incident_date = Column(DateTime(timezone=True), nullable=True)

    # AI Analysis
    risk_score = Column(Float, default=0.0, index=True)
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.LOW)
    ai_summary = Column(Text, nullable=True)
    linked_case_ids = Column(JSON, default=list)
    entity_count = Column(Integer, default=0)

    # Assignment
    submitted_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Metadata
    ip_address = Column(String(45), nullable=True)
    language = Column(String(10), default="en")
    is_anonymous = Column(Boolean, default=False)
    graph_node_id = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    submitted_by = relationship("User", back_populates="complaints", foreign_keys=[submitted_by_id])
    assigned_to = relationship("User", back_populates="assigned_cases", foreign_keys=[assigned_to_id])
    evidence = relationship("Evidence", back_populates="complaint", cascade="all, delete-orphan")
    entities = relationship("ExtractedEntity", back_populates="complaint", cascade="all, delete-orphan")
    notes = relationship("InvestigationNote", back_populates="complaint", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="complaint")

    __table_args__ = (
        Index("ix_complaints_risk_status", "risk_score", "status"),
        Index("ix_complaints_created_category", "created_at", "category"),
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=gen_uuid)
    complaint_id = Column(String, ForeignKey("complaints.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    evidence_type = Column(Enum(EvidenceType), nullable=False)
    file_hash = Column(String(64), nullable=False)           # SHA-256 for chain of custody
    extracted_text = Column(Text, nullable=True)             # OCR / Whisper output
    processing_status = Column(String(50), default="pending")
    processing_error = Column(Text, nullable=True)
    uploaded_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    complaint = relationship("Complaint", back_populates="evidence")
    uploaded_by = relationship("User")


class ExtractedEntity(Base):
    __tablename__ = "extracted_entities"

    id = Column(String, primary_key=True, default=gen_uuid)
    complaint_id = Column(String, ForeignKey("complaints.id"), nullable=False, index=True)
    entity_type = Column(Enum(EntityType), nullable=False, index=True)
    value = Column(String(500), nullable=False, index=True)
    normalized_value = Column(String(500), nullable=True)
    confidence = Column(Float, default=1.0)
    source = Column(String(50), default="nlp")              # nlp | ocr | stt | manual
    context_snippet = Column(Text, nullable=True)
    risk_score = Column(Float, default=0.0)
    occurrence_count = Column(Integer, default=1)
    graph_node_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    complaint = relationship("Complaint", back_populates="entities")

    __table_args__ = (
        Index("ix_entity_type_value", "entity_type", "value"),
        Index("ix_entity_complaint_type", "complaint_id", "entity_type"),
    )


class CaseLink(Base):
    __tablename__ = "case_links"

    id = Column(String, primary_key=True, default=gen_uuid)
    complaint_a_id = Column(String, ForeignKey("complaints.id"), nullable=False)
    complaint_b_id = Column(String, ForeignKey("complaints.id"), nullable=False)
    link_type = Column(String(100), nullable=False)         # shared_entity | pattern | campaign
    shared_entities = Column(JSON, default=list)
    similarity_score = Column(Float, default=0.0)
    confirmed_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    is_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_case_links_complaints", "complaint_a_id", "complaint_b_id", unique=True),
    )


class InvestigationNote(Base):
    __tablename__ = "investigation_notes"

    id = Column(String, primary_key=True, default=gen_uuid)
    complaint_id = Column(String, ForeignKey("complaints.id"), nullable=False, index=True)
    author_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    complaint = relationship("Complaint", back_populates="notes")
    author = relationship("User")


class ThreatCampaign(Base):
    __tablename__ = "threat_campaigns"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Enum(ComplaintCategory), nullable=True)
    complaint_ids = Column(JSON, default=list)
    entity_signatures = Column(JSON, default=dict)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.LOW)
    total_victims = Column(Integer, default=0)
    total_financial_loss = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    complaint_id = Column(String, ForeignKey("complaints.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="audit_logs")
    complaint = relationship("Complaint", back_populates="audit_logs")
