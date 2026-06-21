import os
import uuid
import aiofiles
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from app.db.postgres import get_db
from app.models.models import (
    Complaint, ExtractedEntity, CaseLink, ThreatCampaign,
    Evidence, AuditLog, User, RiskLevel, ComplaintStatus, EvidenceType
)
from app.schemas.schemas import (
    DashboardStats, GraphData, ThreatCampaignOut, EntitySearchResult, AuditLogOut, EvidenceOut
)
from app.api.deps import get_current_user, require_investigator, require_admin, log_action
from app.core.config import settings
from app.core.security import compute_file_hash
from app.services.correlation.graph_engine import graph_engine
from app.services.extraction.entity_extractor import extractor
from app.services.extraction.evidence_processor import evidence_processor

# ── Dashboard Router ───────────────────────────────────────────────────────
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@dashboard_router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_investigator),
):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total       = (await db.execute(select(func.count(Complaint.id)))).scalar() or 0
    open_c      = (await db.execute(select(func.count(Complaint.id)).where(
                    Complaint.status.in_([ComplaintStatus.SUBMITTED, ComplaintStatus.UNDER_REVIEW,
                                          ComplaintStatus.INVESTIGATING])))).scalar() or 0
    critical    = (await db.execute(select(func.count(Complaint.id)).where(
                    Complaint.risk_level == RiskLevel.CRITICAL))).scalar() or 0
    high        = (await db.execute(select(func.count(Complaint.id)).where(
                    Complaint.risk_level == RiskLevel.HIGH))).scalar() or 0
    resolved    = (await db.execute(select(func.count(Complaint.id)).where(
                    Complaint.status == ComplaintStatus.RESOLVED))).scalar() or 0
    entities    = (await db.execute(select(func.count(ExtractedEntity.id)))).scalar() or 0
    links       = (await db.execute(select(func.count(CaseLink.id)))).scalar() or 0
    campaigns   = (await db.execute(select(func.count(ThreatCampaign.id)).where(
                    ThreatCampaign.is_active == True))).scalar() or 0
    fin_loss_r  = await db.execute(select(func.sum(Complaint.financial_loss)))
    fin_loss    = fin_loss_r.scalar() or 0.0
    today_c     = (await db.execute(select(func.count(Complaint.id)).where(
                    Complaint.created_at >= today))).scalar() or 0

    graph_stats = await graph_engine.get_graph_stats()

    return DashboardStats(
        total_complaints=total,
        open_complaints=open_c,
        critical_complaints=critical,
        high_risk_complaints=high,
        resolved_complaints=resolved,
        total_entities_extracted=entities,
        linked_case_pairs=links,
        active_campaigns=campaigns,
        total_financial_loss=fin_loss,
        complaints_today=today_c,
        graph_nodes=graph_stats.get("total_entities", 0) + graph_stats.get("total_complaints", 0),
        graph_edges=graph_stats.get("total_links", 0),
    )


@dashboard_router.get("/recent-complaints")
async def recent_complaints(
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_investigator),
):
    result = await db.execute(
        select(Complaint)
        .order_by(desc(Complaint.created_at))
        .limit(limit)
    )
    return result.scalars().all()


@dashboard_router.get("/priority-queue")
async def priority_queue(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_investigator),
):
    """High-risk unassigned complaints — investigator action queue."""
    result = await db.execute(
        select(Complaint)
        .where(
            and_(
                Complaint.assigned_to_id == None,
                Complaint.status.in_([ComplaintStatus.SUBMITTED, ComplaintStatus.UNDER_REVIEW])
            )
        )
        .order_by(desc(Complaint.risk_score))
        .limit(limit)
    )
    return result.scalars().all()


@dashboard_router.get("/trends")
async def complaint_trends(
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_investigator),
):
    """Daily complaint counts for trend charts."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            func.date_trunc("day", Complaint.created_at).label("day"),
            func.count(Complaint.id).label("count"),
            func.avg(Complaint.risk_score).label("avg_risk"),
        )
        .where(Complaint.created_at >= since)
        .group_by(func.date_trunc("day", Complaint.created_at))
        .order_by(func.date_trunc("day", Complaint.created_at))
    )
    return [{"day": str(r.day), "count": r.count, "avg_risk": round(r.avg_risk or 0, 3)}
            for r in result.all()]


# ── Graph Router ───────────────────────────────────────────────────────────
graph_router = APIRouter(prefix="/graph", tags=["Graph Intelligence"])

@graph_router.get("/full", response_model=GraphData)
async def full_graph(
    limit: int = Query(200, le=500),
    current_user: User = Depends(require_investigator),
):
    return await graph_engine.get_full_graph(limit=limit)


@graph_router.get("/complaint/{complaint_id}/network")
async def complaint_network(
    complaint_id: str,
    current_user: User = Depends(require_investigator),
):
    related = await graph_engine.find_related_complaints(complaint_id, min_shared=1, limit=50)
    return {"complaint_id": complaint_id, "related": related}


@graph_router.get("/entity/{entity_type}/{value}/profile")
async def entity_profile(
    entity_type: str,
    value: str,
    current_user: User = Depends(require_investigator),
):
    profile = await graph_engine.get_entity_risk_profile(entity_type, value)
    if not profile:
        raise HTTPException(404, "Entity not found in graph.")
    return profile


@graph_router.get("/campaigns")
async def detected_campaigns(
    min_complaints: int = Query(3, ge=2),
    current_user: User = Depends(require_investigator),
):
    return await graph_engine.detect_campaigns(min_complaints=min_complaints)


@graph_router.get("/stats")
async def graph_stats(current_user: User = Depends(require_investigator)):
    return await graph_engine.get_graph_stats()


# ── Intelligence / Search Router ───────────────────────────────────────────
intel_router = APIRouter(prefix="/intelligence", tags=["Threat Intelligence"])

@intel_router.get("/search-entity")
async def search_entity(
    entity_type: str,
    value: str,
    current_user: User = Depends(require_investigator),
    db: AsyncSession = Depends(get_db),
):
    """Search for an entity across all complaints."""
    result = await db.execute(
        select(ExtractedEntity)
        .where(
            and_(
                ExtractedEntity.entity_type == entity_type,
                ExtractedEntity.normalized_value.ilike(f"%{value}%"),
            )
        )
        .order_by(desc(ExtractedEntity.risk_score))
        .limit(50)
    )
    entities = result.scalars().all()

    graph_profile = await graph_engine.get_entity_risk_profile(entity_type, value)

    return {
        "matches": entities,
        "graph_profile": graph_profile,
        "total": len(entities),
    }


@intel_router.post("/extract-text")
async def extract_from_text(
    text: str,
    current_user: User = Depends(require_investigator),
):
    """Ad-hoc entity extraction from arbitrary text — for investigator analysis."""
    entities = extractor.extract(text, source="manual")
    keywords = extractor.extract_keywords(text)
    return {
        "entities": [e.__dict__ for e in entities],
        "keywords": keywords,
        "entity_count": len(entities),
    }


@intel_router.get("/campaigns", response_model=list[ThreatCampaignOut])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_investigator),
):
    result = await db.execute(
        select(ThreatCampaign)
        .where(ThreatCampaign.is_active == True)
        .order_by(desc(ThreatCampaign.risk_score))
    )
    return result.scalars().all()


# ── Evidence Router ────────────────────────────────────────────────────────
evidence_router = APIRouter(prefix="/evidence", tags=["Evidence Management"])

MIME_TO_TYPE = {
    "image/jpeg": EvidenceType.IMAGE, "image/png": EvidenceType.IMAGE,
    "image/gif": EvidenceType.IMAGE,  "image/webp": EvidenceType.IMAGE,
    "application/pdf": EvidenceType.DOCUMENT,
    "application/msword": EvidenceType.DOCUMENT,
    "text/plain": EvidenceType.DOCUMENT,
    "audio/mpeg": EvidenceType.AUDIO, "audio/wav": EvidenceType.AUDIO,
    "audio/ogg": EvidenceType.AUDIO,  "video/mp4": EvidenceType.VIDEO,
}


@evidence_router.post("/upload/{complaint_id}", response_model=EvidenceOut, status_code=201)
async def upload_evidence(
    complaint_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate file type
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in settings.allowed_extensions_set:
        raise HTTPException(400, f"File type '.{ext}' not allowed.")

    # Read file
    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(413, f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit.")

    # Compute hash for chain of custody
    file_hash = compute_file_hash(content)

    # Save to disk
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    evidence_type = MIME_TO_TYPE.get(file.content_type, EvidenceType.OTHER)

    ev = Evidence(
        complaint_id=complaint_id,
        file_name=safe_name,
        original_name=file.filename,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        evidence_type=evidence_type,
        file_hash=file_hash,
        uploaded_by_id=current_user.id,
        processing_status="processing",
    )
    db.add(ev)
    await db.flush()

    # Process evidence (OCR / STT) synchronously for now
    proc_result = evidence_processor.process(file_path, file.content_type or "")
    ev.extracted_text = proc_result.get("extracted_text", "")
    ev.processing_status = "completed" if not proc_result.get("error") else "error"
    ev.processing_error = proc_result.get("error")

    # If text was extracted, run entity extraction on it
    if ev.extracted_text:
        from app.models.models import ExtractedEntity as EE
        entities = extractor.extract(ev.extracted_text, source="ocr")
        for ent in entities:
            db.add(EE(
                complaint_id=complaint_id,
                entity_type=ent.entity_type,
                value=ent.value,
                normalized_value=ent.normalized_value,
                confidence=ent.confidence,
                source="ocr",
                context_snippet=ent.context_snippet[:500] if ent.context_snippet else "",
            ))

    await log_action(db, current_user.id, "EVIDENCE_UPLOADED",
                     resource_type="evidence", resource_id=ev.id,
                     complaint_id=complaint_id)
    await db.commit()
    await db.refresh(ev)
    return ev


@evidence_router.get("/complaint/{complaint_id}", response_model=list[EvidenceOut])
async def list_evidence(
    complaint_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Evidence)
        .where(Evidence.complaint_id == complaint_id)
        .order_by(desc(Evidence.created_at))
    )
    return result.scalars().all()


# ── Audit Router ───────────────────────────────────────────────────────────
audit_router = APIRouter(prefix="/audit", tags=["Audit Trail"])

@audit_router.get("/logs", response_model=list[AuditLogOut])
async def get_audit_logs(
    limit: int = Query(50, le=200),
    complaint_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_investigator),
):
    query = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
    if complaint_id:
        query = query.where(AuditLog.complaint_id == complaint_id)
    result = await db.execute(query)
    return result.scalars().all()
