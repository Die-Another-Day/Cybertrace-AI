import math
import random
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, and_, or_

from app.db.postgres import get_db
from app.models.models import (
    Complaint, User, ExtractedEntity, CaseLink, InvestigationNote,
    UserRole, ComplaintStatus, RiskLevel
)
from app.schemas.schemas import (
    ComplaintCreate, ComplaintUpdate, ComplaintOut, ComplaintListOut,
    EntityOut, CaseLinkOut, NoteCreate, NoteOut, ProcessingResult
)
from app.api.deps import get_current_user, require_investigator, log_action
from app.services.complaint_processor import complaint_processor

router = APIRouter(prefix="/complaints", tags=["Complaints"])


def _gen_number():
    now = datetime.now(timezone.utc)
    return f"CYB-{now.year}-{now.month:02d}-{random.randint(10000, 99999)}"


# ── Submit Complaint ───────────────────────────────────────────────────────
@router.post("/", response_model=ComplaintOut, status_code=201)
async def submit_complaint(
    payload: ComplaintCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = Complaint(
        complaint_number=_gen_number(),
        title=payload.title,
        description=payload.description,
        category=payload.category,
        victim_name=payload.victim_name,
        victim_phone=payload.victim_phone,
        victim_email=payload.victim_email,
        victim_address=payload.victim_address,
        financial_loss=payload.financial_loss,
        incident_date=payload.incident_date,
        is_anonymous=payload.is_anonymous,
        language=payload.language,
        submitted_by_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    db.add(complaint)
    await db.flush()

    await log_action(
        db, current_user.id, "COMPLAINT_SUBMITTED",
        resource_type="complaint", resource_id=complaint.id,
        complaint_id=complaint.id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(complaint)

    # Run AI processing in background
    background_tasks.add_task(_process_async, complaint.id)

    return complaint


async def _process_async(complaint_id: str):
    """Background task: AI entity extraction + graph correlation + risk scoring."""
    from app.db.postgres import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            await complaint_processor.process(complaint_id, db)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Processing error {complaint_id}: {e}")


# ── List Complaints ────────────────────────────────────────────────────────
@router.get("/", response_model=ComplaintListOut)
async def list_complaints(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at", enum=["created_at", "risk_score", "financial_loss"]),
    sort_order: str = Query("desc", enum=["asc", "desc"]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Complaint)

    # Citizens only see their own complaints
    if current_user.role == UserRole.CITIZEN:
        query = query.where(Complaint.submitted_by_id == current_user.id)

    if status:
        query = query.where(Complaint.status == status)
    if category:
        query = query.where(Complaint.category == category)
    if risk_level:
        query = query.where(Complaint.risk_level == risk_level)
    if search:
        query = query.where(
            or_(
                Complaint.title.ilike(f"%{search}%"),
                Complaint.description.ilike(f"%{search}%"),
                Complaint.complaint_number.ilike(f"%{search}%"),
            )
        )

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Sort
    sort_col = getattr(Complaint, sort_by)
    query = query.order_by(desc(sort_col) if sort_order == "desc" else asc(sort_col))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    return ComplaintListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
    )


# ── Get Single Complaint ───────────────────────────────────────────────────
@router.get("/{complaint_id}", response_model=ComplaintOut)
async def get_complaint(
    complaint_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = await db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(404, "Complaint not found.")
    if current_user.role == UserRole.CITIZEN and complaint.submitted_by_id != current_user.id:
        raise HTTPException(403, "Access denied.")
    return complaint


# ── Update Complaint ───────────────────────────────────────────────────────
@router.patch("/{complaint_id}", response_model=ComplaintOut)
async def update_complaint(
    complaint_id: str,
    payload: ComplaintUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_investigator),
):
    complaint = await db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(404, "Complaint not found.")

    if payload.status:
        complaint.status = payload.status
    if payload.assigned_to_id:
        complaint.assigned_to_id = payload.assigned_to_id
    if payload.title:
        complaint.title = payload.title
    if payload.description:
        complaint.description = payload.description

    await log_action(
        db, current_user.id, "COMPLAINT_UPDATED",
        resource_type="complaint", resource_id=complaint_id,
        complaint_id=complaint_id,
        details=payload.model_dump(exclude_none=True),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(complaint)
    return complaint


# ── Trigger Manual Re-processing ───────────────────────────────────────────
@router.post("/{complaint_id}/process", response_model=ProcessingResult)
async def reprocess_complaint(
    complaint_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_investigator),
):
    complaint = await db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(404, "Complaint not found.")
    result = await complaint_processor.process(complaint_id, db)
    return result


# ── Get Complaint Entities ─────────────────────────────────────────────────
@router.get("/{complaint_id}/entities", response_model=list[EntityOut])
async def get_entities(
    complaint_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ExtractedEntity)
        .where(ExtractedEntity.complaint_id == complaint_id)
        .order_by(desc(ExtractedEntity.risk_score))
    )
    return result.scalars().all()


# ── Get Related Cases ──────────────────────────────────────────────────────
@router.get("/{complaint_id}/related", response_model=list[CaseLinkOut])
async def get_related_cases(
    complaint_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_investigator),
):
    result = await db.execute(
        select(CaseLink).where(
            or_(
                CaseLink.complaint_a_id == complaint_id,
                CaseLink.complaint_b_id == complaint_id,
            )
        ).order_by(desc(CaseLink.similarity_score))
    )
    return result.scalars().all()


# ── Investigation Notes ────────────────────────────────────────────────────
@router.post("/{complaint_id}/notes", response_model=NoteOut, status_code=201)
async def add_note(
    complaint_id: str,
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_investigator),
):
    complaint = await db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(404, "Complaint not found.")
    note = InvestigationNote(
        complaint_id=complaint_id,
        author_id=current_user.id,
        content=payload.content,
        is_internal=payload.is_internal,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.get("/{complaint_id}/notes", response_model=list[NoteOut])
async def get_notes(
    complaint_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(InvestigationNote).where(
        InvestigationNote.complaint_id == complaint_id
    )
    if current_user.role == UserRole.CITIZEN:
        query = query.where(InvestigationNote.is_internal == False)
    result = await db.execute(query.order_by(desc(InvestigationNote.created_at)))
    return result.scalars().all()
