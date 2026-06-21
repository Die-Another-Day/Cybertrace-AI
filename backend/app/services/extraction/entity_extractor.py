"""
CyberTrace AI – Entity Extraction Service
Extracts cyber indicators from text using NLP (spaCy NER),
regex patterns, and domain-specific validators.
"""
import re
import logging
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
import phonenumbers
import tldextract

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntityResult:
    entity_type: str
    value: str
    normalized_value: str
    confidence: float
    source: str
    context_snippet: str = ""


# ── Regex Patterns ────────────────────────────────────────────────────────
PATTERNS = {
    "phone_number": [
        r"\b(?:\+91|91|0)?[6-9]\d{9}\b",                         # Indian mobile
        r"\b(?:\+1)?[2-9]\d{2}[2-9]\d{6}\b",                     # US format
        r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",                    # Generic
    ],
    "upi_id": [
        r"\b[a-zA-Z0-9._-]+@(?:okaxis|oksbi|okicici|okhdfcbank|paytm|ybl|ibl|axl|upi|apl|barodampay|" \
        r"centralbank|cnrb|eazypay|equitas|fbl|idbi|idfc|indus|jkb|karb|kmb|kotak|lvb|mahb|" \
        r"nsdl|pingpay|psb|rbl|sbi|sc|sib|tjsb|uco|unionbank|utbi|vijb)\b",
        r"\b[a-zA-Z0-9._-]{3,256}@[a-zA-Z]{3,64}\b",            # Generic UPI
    ],
    "email": [
        r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b",
    ],
    "ip_address": [
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b",
        r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b",       # IPv6
    ],
    "bank_account": [
        r"\b\d{9,18}\b(?=.*(?:account|a/c|acct|bank))",          # With context
        r"(?:account|a/c|acct)\s*(?:no\.?|number)?\s*:?\s*(\d{9,18})\b",
    ],
    "ifsc_code": [
        r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
    ],
    "url": [
        r"https?://[^\s<>\"{}|\\^`\[\]]+",
        r"(?:www\.)[a-zA-Z0-9-]+(?:\.[a-zA-Z]{2,})+(?:/[^\s]*)?",
    ],
    "social_handle": [
        r"@[a-zA-Z0-9_]{1,50}(?=\s|$|[^a-zA-Z0-9_])",
        r"(?:facebook\.com|fb\.com|instagram\.com|twitter\.com|x\.com|t\.me|telegram\.me)" \
        r"/[a-zA-Z0-9_.]+",
        r"(?:whatsapp|telegram|signal)\s*:?\s*(?:\+?[\d\s\-]{10,15})",
    ],
    "domain": [
        r"\b(?:[a-zA-Z0-9-]+\.)+(?:com|in|org|net|gov|edu|co\.in|io|xyz|online|site|info)\b",
    ],
}

# ── Cyber-specific suspicious keywords ────────────────────────────────────
SUSPICIOUS_KEYWORDS = {
    "financial": ["kyc", "otp", "pin", "cvv", "lottery", "prize", "reward",
                  "refund", "cashback", "investment", "profit", "return",
                  "job offer", "work from home", "part time"],
    "urgency": ["urgent", "immediately", "expire", "block", "suspend",
                "verify now", "act now", "limited time", "last chance"],
    "impersonation": ["rbi", "sebi", "irdai", "trai", "income tax", "cbi",
                      "police", "customs", "courier", "amazon", "flipkart",
                      "paytm", "google pay", "phonepe", "sbi", "hdfc", "icici"],
    "methods": ["screen share", "anydesk", "teamviewer", "remote access",
                "qr code", "link click", "download app", "install"],
}


class EntityExtractor:
    """
    Multi-source entity extractor for cybercrime complaints.
    Supports text (NLP + regex), and outputs structured entity results.
    """

    def __init__(self):
        self._nlp = None
        self._load_nlp()

    def _load_nlp(self):
        try:
            import spacy
            try:
                self._nlp = spacy.load("en_core_web_sm")
                logger.info("spaCy model loaded: en_core_web_sm")
            except OSError:
                logger.warning("spaCy model not found. Using regex-only extraction.")
                self._nlp = None
        except ImportError:
            logger.warning("spaCy not installed. Using regex-only extraction.")
            self._nlp = None

    def extract(self, text: str, source: str = "nlp") -> List[ExtractedEntityResult]:
        """Main extraction entry point."""
        if not text or not text.strip():
            return []

        results: List[ExtractedEntityResult] = []
        seen: set = set()

        # 1. Regex-based extraction
        results.extend(self._regex_extract(text, source))

        # 2. spaCy NER for persons, organizations, locations
        if self._nlp:
            results.extend(self._spacy_extract(text, source))

        # 3. Phone number validation via phonenumbers lib
        results.extend(self._phone_extract(text, source))

        # 4. Deduplicate
        unique = []
        for r in results:
            key = (r.entity_type, r.normalized_value or r.value)
            if key not in seen:
                seen.add(key)
                unique.append(r)

        return unique

    def _regex_extract(self, text: str, source: str) -> List[ExtractedEntityResult]:
        results = []
        for entity_type, patterns in PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    value = match.group(0).strip()
                    if not value or len(value) < 3:
                        continue

                    # Skip emails caught by domain pattern
                    if entity_type == "domain" and "@" in value:
                        continue

                    normalized = self._normalize(entity_type, value)
                    context = self._get_context(text, match.start(), match.end())
                    confidence = self._confidence(entity_type, value, context)

                    results.append(ExtractedEntityResult(
                        entity_type=entity_type,
                        value=value,
                        normalized_value=normalized,
                        confidence=confidence,
                        source=source,
                        context_snippet=context,
                    ))
        return results

    def _spacy_extract(self, text: str, source: str) -> List[ExtractedEntityResult]:
        results = []
        doc = self._nlp(text)
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "GPE", "LOC"):
                results.append(ExtractedEntityResult(
                    entity_type="keyword",
                    value=ent.text,
                    normalized_value=ent.text.lower().strip(),
                    confidence=0.75,
                    source="spacy_ner",
                    context_snippet=text[max(0, ent.start_char - 40):ent.end_char + 40],
                ))
        return results

    def _phone_extract(self, text: str, source: str) -> List[ExtractedEntityResult]:
        """Use phonenumbers library for robust Indian/international phone extraction."""
        results = []
        for match in phonenumbers.PhoneNumberMatcher(text, "IN"):
            number = phonenumbers.format_number(
                match.number, phonenumbers.PhoneNumberFormat.E164
            )
            context = self._get_context(text, match.start, match.end)
            results.append(ExtractedEntityResult(
                entity_type="phone_number",
                value=match.raw_string,
                normalized_value=number,
                confidence=0.95,
                source=source,
                context_snippet=context,
            ))
        return results

    def _normalize(self, entity_type: str, value: str) -> str:
        value = value.strip()
        if entity_type == "email":
            return value.lower()
        if entity_type == "upi_id":
            return value.lower()
        if entity_type == "url":
            return value.lower().rstrip("/")
        if entity_type == "domain":
            extracted = tldextract.extract(value)
            if extracted.domain and extracted.suffix:
                return f"{extracted.domain}.{extracted.suffix}".lower()
            return value.lower()
        if entity_type == "ip_address":
            return value.strip()
        if entity_type == "ifsc_code":
            return value.upper()
        if entity_type == "bank_account":
            return re.sub(r"\D", "", value)
        if entity_type == "phone_number":
            digits = re.sub(r"\D", "", value)
            if digits.startswith("91") and len(digits) == 12:
                return f"+{digits}"
            if len(digits) == 10 and digits[0] in "6789":
                return f"+91{digits}"
            return digits
        return value.lower()

    def _get_context(self, text: str, start: int, end: int, window: int = 60) -> str:
        left = max(0, start - window)
        right = min(len(text), end + window)
        snippet = text[left:right].replace("\n", " ").strip()
        return f"...{snippet}..." if left > 0 or right < len(text) else snippet

    def _confidence(self, entity_type: str, value: str, context: str) -> float:
        base = {
            "upi_id": 0.95,
            "ifsc_code": 0.98,
            "email": 0.92,
            "ip_address": 0.90,
            "url": 0.88,
            "phone_number": 0.80,
            "bank_account": 0.70,
            "domain": 0.75,
            "social_handle": 0.72,
            "keyword": 0.60,
        }.get(entity_type, 0.65)

        # Boost if surrounded by relevant keywords
        ctx_lower = context.lower()
        boosters = ["sent", "received", "transfer", "paid", "fraud", "scam",
                    "account", "upi", "payment", "called", "messaged", "email"]
        if any(b in ctx_lower for b in boosters):
            base = min(1.0, base + 0.08)

        return round(base, 3)

    def extract_keywords(self, text: str) -> List[Dict]:
        """Extract suspicious keywords and phrases."""
        found = []
        text_lower = text.lower()
        for category, keywords in SUSPICIOUS_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    idx = text_lower.index(kw)
                    found.append({
                        "keyword": kw,
                        "category": category,
                        "context": self._get_context(text, idx, idx + len(kw)),
                    })
        return found


# Singleton
extractor = EntityExtractor()
