"""
CyberTrace AI – Complaint Processing Orchestrator
Coordinates entity extraction → graph ingestion → risk scoring
for every complaint submitted to the platform.
"""
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.models.models import (
    Complaint, ExtractedEntity, CaseLink, ThreatCampaign,
    EntityType, RiskLevel, ComplaintStatus
)
from app.services.extraction.entity_extractor import extractor
from app.services.correlation.graph_engine import graph_engine
from app.services.scoring.risk_engine import risk_engine, RiskFactors, CATEGORY_SEVERITY

logger = logging.getLogger(__name__)


def _generate_complaint_number() -> str:
    now = datetime.now(timezone.utc)
    import random
    return f"CYB-{now.year}-{now.month:02d}-{random.randint(10000, 99999)}"


class ComplaintProcessor:
    """
    Full pipeline:
    1. Extract entities from complaint text
    2. Ingest complaint + entities into Neo4j graph
    3. Find related complaints via graph correlation
    4. Compute risk score
    5. Persist everything to PostgreSQL
    6. Detect and update threat campaigns
    """

    async def process(self, complaint_id: str, db: AsyncSession) -> dict:
        logger.info(f"Processing complaint: {complaint_id}")
        result = {
            "complaint_id": complaint_id,
            "entities_found": 0,
            "related_complaints": [],
            "risk_score": 0.0,
            "risk_level": "low",
            "recommendations": [],
            "campaigns_detected": [],
        }

        # 1. Load complaint
        complaint = await db.get(Complaint, complaint_id)
        if not complaint:
            logger.error(f"Complaint {complaint_id} not found.")
            return result

        # 2. Extract entities from description
        full_text = f"{complaint.title} {complaint.description}"
        if complaint.victim_phone:
            full_text += f" {complaint.victim_phone}"
        if complaint.victim_email:
            full_text += f" {complaint.victim_email}"

        entities = extractor.extract(full_text, source="nlp")
        keywords = extractor.extract_keywords(full_text)

        # 3. Persist entities to PostgreSQL
        db_entities = []
        for ent in entities:
            db_ent = ExtractedEntity(
                complaint_id=complaint_id,
                entity_type=ent.entity_type,
                value=ent.value,
                normalized_value=ent.normalized_value,
                confidence=ent.confidence,
                source=ent.source,
                context_snippet=ent.context_snippet[:500] if ent.context_snippet else "",
            )
            db.add(db_ent)
            db_entities.append(db_ent)

        # 4. Add complaint node to Neo4j
        await graph_engine.add_complaint_node(
            complaint_id,
            {
                "complaint_number": complaint.complaint_number or _generate_complaint_number(),
                "category": complaint.category.value if complaint.category else "other",
                "status": complaint.status.value if complaint.status else "submitted",
                "risk_score": 0.0,
                "created_at": str(complaint.created_at or datetime.now(timezone.utc)),
                "financial_loss": complaint.financial_loss or 0.0,
            }
        )

        # 5. Add entity nodes + link to complaint in Neo4j
        for ent in entities:
            await graph_engine.add_entity_node(
                entity_type=ent.entity_type,
                value=ent.value,
                normalized_value=ent.normalized_value or ent.value,
                confidence=ent.confidence,
                risk_score=0.0,
            )
            await graph_engine.link_entity_to_complaint(
                complaint_id=complaint_id,
                entity_type=ent.entity_type,
                normalized_value=ent.normalized_value or ent.value,
                source=ent.source,
            )

        # 6. Find related complaints via graph
        related = await graph_engine.find_related_complaints(complaint_id, min_shared=1)
        result["related_complaints"] = related

        # 7. Compute risk score
        entity_dicts = [
            {"entity_type": e.entity_type, "confidence": e.confidence}
            for e in entities
        ]
        entity_types = {e.entity_type for e in entities}
        factors = RiskFactors(
            entity_count=len(entities),
            financial_loss=complaint.financial_loss or 0.0,
            linked_complaint_count=len(related),
            keyword_hit_count=len(keywords),
            recurring_entities=sum(
                1 for r in related if r.get("shared_count", 0) > 1
            ),
            category_severity=CATEGORY_SEVERITY.get(
                complaint.category.value if complaint.category else "other", 0.5
            ),
            has_upi="upi_id" in entity_types,
            has_bank_account="bank_account" in entity_types,
            has_ip="ip_address" in entity_types,
            has_url="url" in entity_types,
        )
        scoring = risk_engine.compute_score(factors, entity_dicts, related)

        # 8. Update complaint in PostgreSQL
        complaint.risk_score = scoring["risk_score"]
        complaint.risk_level = RiskLevel(scoring["risk_level"])
        complaint.entity_count = len(entities)
        complaint.linked_case_ids = [r["complaint_id"] for r in related]
        complaint.ai_summary = self._generate_summary(complaint, entities, related, scoring)
        complaint.status = ComplaintStatus.UNDER_REVIEW

        # 9. Update entity risk scores in Neo4j
        for ent in entities:
            entity_risk = risk_engine.compute_entity_risk(
                ent.entity_type,
                seen_count=1,
                complaint_risk_scores=[scoring["risk_score"]],
            )
            await db.execute(
                update(ExtractedEntity)
                .where(
                    ExtractedEntity.complaint_id == complaint_id,
                    ExtractedEntity.entity_type == ent.entity_type,
                    ExtractedEntity.normalized_value == (ent.normalized_value or ent.value),
                )
                .values(risk_score=entity_risk)
            )

        # 10. Create CaseLinks for related complaints
        for rel in related:
            existing = await db.execute(
                select(CaseLink).where(
                    ((CaseLink.complaint_a_id == complaint_id) &
                     (CaseLink.complaint_b_id == rel["complaint_id"])) |
                    ((CaseLink.complaint_a_id == rel["complaint_id"]) &
                     (CaseLink.complaint_b_id == complaint_id))
                )
            )
            if not existing.scalar_one_or_none():
                link = CaseLink(
                    complaint_a_id=complaint_id,
                    complaint_b_id=rel["complaint_id"],
                    link_type="shared_entity",
                    shared_entities=rel.get("shared_entities", []),
                    similarity_score=min(rel.get("shared_count", 1) / 5.0, 1.0),
                )
                db.add(link)

        # 11. Detect campaigns
        campaigns = await graph_engine.detect_campaigns(min_complaints=3)
        result["campaigns_detected"] = campaigns[:5]

        await db.commit()

        result.update({
            "entities_found": len(entities),
            "risk_score": scoring["risk_score"],
            "risk_level": scoring["risk_level"],
            "recommendations": scoring["recommendations"],
        })
        logger.info(
            f"Complaint {complaint_id} processed: "
            f"{len(entities)} entities, risk={scoring['risk_score']}, "
            f"{len(related)} related"
        )
        return result

    def _generate_summary(
        self, complaint, entities, related, scoring
    ) -> str:
        entity_types = list({e.entity_type for e in entities})
        summary_parts = [
            f"AI Analysis: {scoring['risk_level'].upper()} risk complaint "
            f"(score: {scoring['risk_score']:.2f}).",
        ]
        if entities:
            summary_parts.append(
                f"Extracted {len(entities)} cyber indicator(s): "
                f"{', '.join(entity_types[:5])}."
            )
        if related:
            summary_parts.append(
                f"Linked to {len(related)} related complaint(s) via shared indicators."
            )
        if complaint.financial_loss:
            summary_parts.append(
                f"Reported financial loss: ₹{complaint.financial_loss:,.2f}."
            )
        return " ".join(summary_parts)


complaint_processor = ComplaintProcessor()
