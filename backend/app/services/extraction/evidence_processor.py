"""
CyberTrace AI – Evidence Processing Service
Handles OCR (Tesseract) for images/PDFs and
Speech-to-Text (Whisper) for audio evidence.
"""
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class OCRProcessor:
    """Extract text from image and document evidence using Tesseract."""

    def __init__(self):
        self._available = self._check_tesseract()

    def _check_tesseract(self) -> bool:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            logger.warning("Tesseract not available. OCR disabled.")
            return False

    def extract_text(self, file_path: str, mime_type: str) -> Tuple[str, float]:
        """
        Returns (extracted_text, confidence_score).
        Supports: images (jpg/png/tiff/bmp), PDF.
        """
        if not self._available:
            return "", 0.0

        try:
            import pytesseract
            from PIL import Image

            path = Path(file_path)
            if not path.exists():
                return "", 0.0

            if mime_type in ("image/jpeg", "image/png", "image/tiff", "image/bmp", "image/webp"):
                return self._ocr_image(path, pytesseract, Image)
            elif mime_type == "application/pdf":
                return self._ocr_pdf(path, pytesseract, Image)
            else:
                return "", 0.0

        except Exception as e:
            logger.error(f"OCR error for {file_path}: {e}")
            return "", 0.0

    def _ocr_image(self, path: Path, pytesseract, Image) -> Tuple[str, float]:
        img = Image.open(path)
        # Preprocess: convert to grayscale for better OCR accuracy
        if img.mode != "RGB":
            img = img.convert("RGB")

        # OCR with confidence data
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT,
                                          lang="eng+hin")
        text = pytesseract.image_to_string(img, lang="eng+hin")

        # Calculate mean confidence (filter out -1 entries)
        confs = [int(c) for c in data["conf"] if int(c) > 0]
        confidence = (sum(confs) / len(confs) / 100) if confs else 0.0

        return text.strip(), round(confidence, 3)

    def _ocr_pdf(self, path: Path, pytesseract, Image) -> Tuple[str, float]:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            all_text = []
            for page in doc:
                text = page.get_text()
                if text.strip():
                    all_text.append(text)
                else:
                    # Render page as image and OCR
                    pix = page.get_pixmap(dpi=200)
                    img_path = tempfile.mktemp(suffix=".png")
                    pix.save(img_path)
                    page_text, _ = self._ocr_image(Path(img_path), pytesseract, Image)
                    all_text.append(page_text)
                    os.unlink(img_path)
            return "\n\n".join(all_text), 0.85
        except ImportError:
            logger.warning("PyMuPDF not installed. PDF OCR unavailable.")
            return "", 0.0


class SpeechToTextProcessor:
    """Transcribe audio evidence using OpenAI Whisper."""

    def __init__(self):
        self._model = None
        self._available = self._check_whisper()

    def _check_whisper(self) -> bool:
        try:
            import whisper
            return True
        except ImportError:
            logger.warning("Whisper not installed. Audio transcription disabled.")
            return False

    def _load_model(self):
        if self._model is None and self._available:
            import whisper
            # Use 'base' model for balance of speed/accuracy
            self._model = whisper.load_model("base")
            logger.info("Whisper model loaded: base")

    def transcribe(self, file_path: str) -> Tuple[str, float, str]:
        """
        Returns (transcribed_text, confidence, detected_language).
        Supports: mp3, wav, ogg, mp4, m4a.
        """
        if not self._available:
            return "", 0.0, "unknown"

        try:
            self._load_model()
            result = self._model.transcribe(
                file_path,
                language=None,          # Auto-detect
                task="transcribe",
                fp16=False,
                verbose=False,
            )
            text = result.get("text", "").strip()
            language = result.get("language", "unknown")

            # Compute mean segment confidence from logprob
            segments = result.get("segments", [])
            if segments:
                avg_logprob = sum(s.get("avg_logprob", -1) for s in segments) / len(segments)
                # Convert logprob to rough 0-1 confidence
                confidence = max(0.0, min(1.0, 1.0 + avg_logprob / 5.0))
            else:
                confidence = 0.7

            return text, round(confidence, 3), language

        except Exception as e:
            logger.error(f"Whisper transcription error for {file_path}: {e}")
            return "", 0.0, "unknown"


class EvidenceProcessor:
    """Unified evidence processing coordinator."""

    def __init__(self):
        self.ocr = OCRProcessor()
        self.stt = SpeechToTextProcessor()

    def process(self, file_path: str, mime_type: str) -> dict:
        """
        Process a piece of evidence and return extracted text + metadata.
        """
        result = {
            "extracted_text": "",
            "confidence": 0.0,
            "processing_method": None,
            "language": "unknown",
            "error": None,
        }

        try:
            if mime_type.startswith("image/") or mime_type == "application/pdf":
                text, confidence = self.ocr.extract_text(file_path, mime_type)
                result["extracted_text"] = text
                result["confidence"] = confidence
                result["processing_method"] = "ocr"

            elif mime_type.startswith("audio/") or mime_type in (
                "video/mp4", "audio/mpeg", "audio/wav", "audio/ogg"
            ):
                text, confidence, lang = self.stt.transcribe(file_path)
                result["extracted_text"] = text
                result["confidence"] = confidence
                result["processing_method"] = "whisper_stt"
                result["language"] = lang

            elif mime_type in ("text/plain", "application/msword"):
                with open(file_path, "r", errors="ignore") as f:
                    result["extracted_text"] = f.read()
                result["confidence"] = 1.0
                result["processing_method"] = "direct_read"

        except Exception as e:
            logger.error(f"Evidence processing error: {e}")
            result["error"] = str(e)

        return result


evidence_processor = EvidenceProcessor()
