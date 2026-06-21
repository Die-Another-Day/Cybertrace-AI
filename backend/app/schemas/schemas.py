from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ── Enums (mirrors models) ─────────────────────────────────────────────────
class UserRole(str, Enum):
    CITIZEN = "citizen"
    INVESTIGATOR = "investigator"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"

class ComplaintStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INVESTIGATING = "investigating"
    LINKED = "linked"
    RESOLVED = "resolved"
    CLOSED = "closed"

class ComplaintCategory(str, Enum):
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

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Auth ───────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    role: UserRole = UserRole.CITIZEN
    badge_number: Optional[str] = None
    department: Optional[str] = None
    preferred_language: str = "en"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain an uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain a digit.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    full_name: str


class UserOut(BaseModel):
    id: str
    full_name: str
    email: str
    phone: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    badge_number: Optional[str]
    department: Optional[str]
    preferred_language: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Complaints ─────────────────────────────────────────────────────────────
class ComplaintCreate(BaseModel):
    title: str
    description: str
    category: ComplaintCategory
    victim_name: Optional[str] = None
    victim_phone: Optional[str] = None
    victim_email: Optional[EmailStr] = None
    victim_address: Optional[str] = None
    financial_loss: Optional[float] = None
    incident_date: Optional[datetime] = None
    is_anonymous: bool = False
    language: str = "en"

    @field_validator("description")
    @classmethod
    def description_min(cls, v):
        if len(v.strip()) < 30:
            raise ValueError("Description must be at least 30 characters.")
        return v

    @field_validator("financial_loss")
    @classmethod
    def loss_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("Financial loss cannot be negative.")
        return v


class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatus] = None
    assigned_to_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class ComplaintOut(BaseModel):
    id: str
    complaint_number: str
    title: str
    description: str
    category: ComplaintCategory
    status: ComplaintStatus
    victim_name: Optional[str]
    victim_phone: Optional[str]
    victim_email: Optional[str]
    financial_loss: Optional[float]
    incident_date: Optional[datetime]
    risk_score: float
    risk_level: RiskLevel
    ai_summary: Optional[str]
    linked_case_ids: List[str]
    entity_count: int
    is_anonymous: bool
    language: str
    submitted_by_id: str
    assigned_to_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ComplaintListOut(BaseModel):
    items: List[ComplaintOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Entities ───────────────────────────────────────────────────────────────
class EntityOut(BaseModel):
    id: str
    complaint_id: str
    entity_type: str
    value: str
    normalized_value: Optional[str]
    confidence: float
    source: str
    context_snippet: Optional[str]
    risk_score: float
    occurrence_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Evidence ───────────────────────────────────────────────────────────────
class EvidenceOut(BaseModel):
    id: str
    complaint_id: str
    file_name: str
    original_name: str
    file_size: int
    mime_type: str
    evidence_type: str
    file_hash: str
    extracted_text: Optional[str]
    processing_status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Investigation Notes ────────────────────────────────────────────────────
class NoteCreate(BaseModel):
    content: str
    is_internal: bool = True

class NoteOut(BaseModel):
    id: str
    complaint_id: str
    author_id: str
    content: str
    is_internal: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Case Links ─────────────────────────────────────────────────────────────
class CaseLinkOut(BaseModel):
    id: str
    complaint_a_id: str
    complaint_b_id: str
    link_type: str
    shared_entities: List[Dict]
    similarity_score: float
    is_confirmed: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Dashboard ──────────────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_complaints: int
    open_complaints: int
    critical_complaints: int
    high_risk_complaints: int
    resolved_complaints: int
    total_entities_extracted: int
    linked_case_pairs: int
    active_campaigns: int
    total_financial_loss: float
    complaints_today: int
    graph_nodes: int
    graph_edges: int


class ThreatCampaignOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    complaint_ids: List[str]
    risk_score: float
    risk_level: RiskLevel
    total_victims: int
    total_financial_loss: float
    is_active: bool
    detected_at: datetime

    class Config:
        from_attributes = True


# ── Graph ──────────────────────────────────────────────────────────────────
class GraphData(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


# ── Processing Result ──────────────────────────────────────────────────────
class ProcessingResult(BaseModel):
    complaint_id: str
    entities_found: int
    related_complaints: List[Dict]
    risk_score: float
    risk_level: str
    recommendations: List[str]
    campaigns_detected: List[Dict]


# ── Audit Log ──────────────────────────────────────────────────────────────
class AuditLogOut(BaseModel):
    id: str
    user_id: Optional[str]
    complaint_id: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[Dict]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Search ─────────────────────────────────────────────────────────────────
class EntitySearchResult(BaseModel):
    entity_type: str
    value: str
    risk_score: float
    total_appearances: int
    complaint_ids: List[str]
    first_seen: Optional[str]
    last_seen: Optional[str]
