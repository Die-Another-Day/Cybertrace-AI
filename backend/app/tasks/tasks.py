import asyncio
import logging
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="app.tasks.tasks.process_complaint_task",
                 max_retries=3, default_retry_delay=30)
def process_complaint_task(self, complaint_id: str):
    """
    Full AI pipeline for a single complaint:
    entity extraction → graph ingestion → risk scoring.
    """
    async def _run():
        from app.db.postgres import AsyncSessionLocal
        from app.services.complaint_processor import complaint_processor
        async with AsyncSessionLocal() as db:
            return await complaint_processor.process(complaint_id, db)

    try:
        result = _run_async(_run())
        logger.info(f"Complaint {complaint_id} processed via Celery: {result}")
        return result
    except Exception as exc:
        logger.error(f"Celery task failed for {complaint_id}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, name="app.tasks.tasks.process_evidence_task",
                 max_retries=2, default_retry_delay=60)
def process_evidence_task(self, evidence_id: str):
    """
    OCR / STT processing for uploaded evidence,
    followed by entity extraction on the extracted text.
    """
    async def _run():
        from app.db.postgres import AsyncSessionLocal
        from sqlalchemy import select, update
        from app.models.models import Evidence
        from app.services.extraction.evidence_processor import evidence_processor
        from app.services.extraction.entity_extractor import extractor
        from app.models.models import ExtractedEntity

        async with AsyncSessionLocal() as db:
            ev = await db.get(Evidence, evidence_id)
            if not ev:
                return {"error": "Evidence not found"}

            result = evidence_processor.process(ev.file_path, ev.mime_type)

            ev.extracted_text = result.get("extracted_text", "")
            ev.processing_status = "completed" if not result.get("error") else "error"
            ev.processing_error = result.get("error")

            if ev.extracted_text:
                entities = extractor.extract(ev.extracted_text, source="ocr")
                for ent in entities:
                    db.add(ExtractedEntity(
                        complaint_id=ev.complaint_id,
                        entity_type=ent.entity_type,
                        value=ent.value,
                        normalized_value=ent.normalized_value,
                        confidence=ent.confidence,
                        source="ocr",
                        context_snippet=(ent.context_snippet or "")[:500],
                    ))

            await db.commit()
            return {"evidence_id": evidence_id, "chars_extracted": len(ev.extracted_text or "")}

    try:
        return _run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(name="app.tasks.tasks.detect_campaigns_task")
def detect_campaigns_task():
    """
    Periodic task: run campaign detection across entire graph
    and persist detected campaigns to PostgreSQL.
    """
    async def _run():
        from app.db.postgres import AsyncSessionLocal
        from app.services.correlation.graph_engine import graph_engine
        from app.models.models import ThreatCampaign, RiskLevel

        campaigns = await graph_engine.detect_campaigns(min_complaints=3)

        async with AsyncSessionLocal() as db:
            for c in campaigns[:20]:
                risk = c.get("complaint_count", 0) / 10.0
                risk = min(risk, 1.0)
                level = "critical" if risk >= 0.75 else "high" if risk >= 0.55 else "medium" if risk >= 0.35 else "low"

                campaign = ThreatCampaign(
                    name=f"{c['pivot_entity_type'].replace('_',' ').title()} Campaign — {c['pivot_entity_value'][:30]}",
                    complaint_ids=c.get("complaint_ids", []),
                    entity_signatures={"pivot_type": c["pivot_entity_type"], "pivot_value": c["pivot_entity_value"]},
                    risk_score=risk,
                    risk_level=RiskLevel(level),
                    total_victims=c.get("complaint_count", 0),
                    is_active=True,
                )
                db.add(campaign)
            await db.commit()

        logger.info(f"Campaign detection: {len(campaigns)} campaigns found.")
        return {"campaigns_found": len(campaigns)}

    return _run_async(_run())
