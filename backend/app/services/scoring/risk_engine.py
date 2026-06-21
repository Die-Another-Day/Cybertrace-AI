"""
CyberTrace AI – Risk Scoring Service
ML-based risk scoring for complaints using entity signals,
complaint patterns, financial loss, and graph correlation data.
"""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)


@dataclass
class RiskFactors:
    entity_count: int = 0
    high_risk_entity_types: int = 0
    financial_loss: float = 0.0
    linked_complaint_count: int = 0
    keyword_hit_count: int = 0
    recurring_entities: int = 0        # Entities seen in other complaints
    category_severity: float = 0.5
    has_upi: bool = False
    has_bank_account: bool = False
    has_ip: bool = False
    has_url: bool = False


# Category base severity weights (0.0 – 1.0)
CATEGORY_SEVERITY = {
    "financial_fraud":     0.90,
    "upi_fraud":           0.88,
    "investment_fraud":    0.85,
    "otp_fraud":           0.83,
    "identity_theft":      0.80,
    "ransomware":          0.92,
    "hacking":             0.78,
    "phishing":            0.75,
    "social_media_fraud":  0.65,
    "cyberbullying":       0.55,
    "other":               0.50,
}

# Entity type risk weights
ENTITY_RISK_WEIGHT = {
    "bank_account":   0.90,
    "upi_id":         0.88,
    "ip_address":     0.75,
    "url":            0.70,
    "phone_number":   0.65,
    "email":          0.60,
    "domain":         0.65,
    "social_handle":  0.55,
    "ifsc_code":      0.80,
    "keyword":        0.40,
}

RISK_LEVELS = [
    (0.75, "critical"),
    (0.55, "high"),
    (0.35, "medium"),
    (0.0,  "low"),
]


class RiskScoringEngine:
    """
    Computes a 0.0–1.0 risk score for each complaint.
    Combines rule-based signals with weighted factor analysis.
    """

    def compute_score(
        self,
        factors: RiskFactors,
        entity_list: List[Dict],
        related_complaints: List[Dict],
    ) -> Dict:
        """
        Returns dict with risk_score (float), risk_level (str),
        breakdown (dict of sub-scores), and recommendations (list).
        """
        scores = {}

        # 1. Category severity base
        scores["category"] = factors.category_severity * 0.20

        # 2. Entity diversity & high-risk types
        entity_score = self._entity_score(entity_list)
        scores["entities"] = entity_score * 0.25

        # 3. Financial loss signal
        scores["financial_loss"] = self._financial_score(factors.financial_loss) * 0.20

        # 4. Graph linkage — how many other complaints share entities
        scores["graph_linkage"] = self._linkage_score(
            len(related_complaints), factors.recurring_entities
        ) * 0.20

        # 5. Suspicious keyword density
        scores["keywords"] = min(factors.keyword_hit_count / 10.0, 1.0) * 0.10

        # 6. Presence of critical indicator types
        indicator_bonus = sum([
            0.03 if factors.has_upi else 0,
            0.03 if factors.has_bank_account else 0,
            0.02 if factors.has_ip else 0,
            0.01 if factors.has_url else 0,
        ])
        scores["indicator_bonus"] = min(indicator_bonus, 0.05)

        total = sum(scores.values())
        total = round(min(total, 1.0), 4)
        level = self._get_level(total)

        return {
            "risk_score": total,
            "risk_level": level,
            "breakdown": scores,
            "recommendations": self._recommendations(total, factors, related_complaints),
        }

    def compute_entity_risk(
        self, entity_type: str, seen_count: int, complaint_risk_scores: List[float]
    ) -> float:
        """Risk score for an individual entity node in the graph."""
        base = ENTITY_RISK_WEIGHT.get(entity_type, 0.5)
        # Frequency amplifier: log scale
        freq_factor = min(math.log1p(seen_count) / math.log1p(50), 1.0)
        avg_complaint_risk = (
            sum(complaint_risk_scores) / len(complaint_risk_scores)
            if complaint_risk_scores else 0.5
        )
        score = (base * 0.40) + (freq_factor * 0.35) + (avg_complaint_risk * 0.25)
        return round(min(score, 1.0), 4)

    # ── Internal helpers ───────────────────────────────────────────────────
    def _entity_score(self, entity_list: List[Dict]) -> float:
        if not entity_list:
            return 0.0
        weighted = sum(
            ENTITY_RISK_WEIGHT.get(e.get("entity_type", "keyword"), 0.4)
            * e.get("confidence", 1.0)
            for e in entity_list
        )
        # Normalize: diminishing returns after 10 entities
        normalized = 1.0 - math.exp(-weighted / 5.0)
        return round(normalized, 4)

    def _financial_score(self, loss: float) -> float:
        if not loss or loss <= 0:
            return 0.0
        # Log scale: ₹1000 → ~0.3, ₹1L → ~0.6, ₹10L → ~0.85, ₹1Cr → ~1.0
        score = math.log1p(loss) / math.log1p(10_000_000)
        return round(min(score, 1.0), 4)

    def _linkage_score(self, related_count: int, recurring: int) -> float:
        if related_count == 0 and recurring == 0:
            return 0.0
        # More linked complaints = higher organized crime signal
        score = 1.0 - math.exp(-(related_count * 0.3 + recurring * 0.1))
        return round(min(score, 1.0), 4)

    def _get_level(self, score: float) -> str:
        for threshold, level in RISK_LEVELS:
            if score >= threshold:
                return level
        return "low"

    def _recommendations(
        self, score: float, factors: RiskFactors, related: List[Dict]
    ) -> List[str]:
        recs = []
        if score >= 0.75:
            recs.append("PRIORITY: Assign to senior investigator immediately.")
        if factors.financial_loss > 100_000:
            recs.append("High financial loss — coordinate with bank fraud cell.")
        if len(related) >= 3:
            recs.append(
                f"Linked to {len(related)} related complaints — likely organized campaign. "
                "Consider consolidating into single investigation."
            )
        if factors.has_upi or factors.has_bank_account:
            recs.append("Financial identifiers extracted — initiate bank account freeze request.")
        if factors.has_ip:
            recs.append("IP address identified — initiate ISP data preservation request.")
        if factors.recurring_entities > 0:
            recs.append(
                f"{factors.recurring_entities} entity/entities appear in other complaints — "
                "check for repeat offender pattern."
            )
        if not recs:
            recs.append("Routine complaint — proceed with standard investigation workflow.")
        return recs


risk_engine = RiskScoringEngine()
