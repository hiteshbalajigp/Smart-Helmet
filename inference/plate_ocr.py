"""PaddleOCR-based Indian license plate recognition."""

from __future__ import annotations

import re
from dataclasses import dataclass

import cv2
import numpy as np

from utils.exceptions import OCRValidationError
from utils.logger import get_logger

logger = get_logger(__name__)

CHAR_CORRECTIONS = {
    "O": "0",
    "I": "1",
    "Z": "2",
    "S": "5",
    "B": "8",
    "G": "6",
}


@dataclass
class OCRResult:
    text: str
    raw_text: str
    confidence: float
    is_valid: bool


class PlateOCR:
    """License plate OCR with enhancement and Indian format validation."""

    def __init__(
        self,
        lang: str = "en",
        use_angle_cls: bool = True,
        patterns: list[str] | None = None,
    ) -> None:
        self.patterns = patterns or [
            r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$",
            r"^[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}$",
            r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$",
        ]
        self._ocr = None
        self._init_ocr(lang, use_angle_cls)

    def _init_ocr(self, lang: str, use_angle_cls: bool) -> None:
        try:
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(use_textline_orientation=use_angle_cls, lang=lang)
            logger.info("PaddleOCR initialized")
        except Exception as exc:
            logger.warning("PaddleOCR unavailable: %s", exc)
            self._ocr = None

    def recognize(self, plate_image: np.ndarray) -> OCRResult:
        enhanced = self._enhance_plate(plate_image)
        raw_text, confidence = self._run_ocr(enhanced)
        corrected = self._correct_characters(raw_text)
        is_valid = self._validate_indian_plate(corrected)
        return OCRResult(
            text=corrected,
            raw_text=raw_text,
            confidence=confidence,
            is_valid=is_valid,
        )

    def _enhance_plate(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2,
        )
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    def _run_ocr(self, image: np.ndarray) -> tuple[str, float]:
        if self._ocr is None:
            return "", 0.0
        try:
            if hasattr(self._ocr, "predict"):
                result = self._ocr.predict(image)
            else:
                result = self._ocr.ocr(image, cls=True)
        except Exception as exc:
            logger.debug("OCR inference failed: %s", exc)
            return "", 0.0

        if not result:
            return "", 0.0

        # Handle both legacy list output and newer PaddleX dict output
        lines = result[0] if isinstance(result, list) and result else result
        if isinstance(lines, dict):
            texts = lines.get("rec_texts") or lines.get("texts") or []
            scores = lines.get("rec_scores") or lines.get("scores") or []
            combined = "".join(texts).upper().replace(" ", "").replace("-", "")
            avg_conf = sum(scores) / len(scores) if scores else 0.0
            return combined, float(avg_conf)

        texts: list[str] = []
        confidences: list[float] = []
        for line in lines:
            if not line or len(line) < 2:
                continue
            texts.append(str(line[1][0]))
            confidences.append(float(line[1][1]))
        combined = "".join(texts).upper().replace(" ", "").replace("-", "")
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return combined, avg_conf

    def _correct_characters(self, text: str) -> str:
        """Apply OCR corrections only in numeric segments of Indian plates."""
        if not text:
            return text
        corrected: list[str] = []
        for char in text:
            if char.isalpha() and char in CHAR_CORRECTIONS:
                # Keep letters in alphabetic segments; only fix common OCR confusions in digit zones
                corrected.append(char)
            elif char in CHAR_CORRECTIONS:
                corrected.append(CHAR_CORRECTIONS[char])
            else:
                corrected.append(char)
        return "".join(corrected).upper()

    def _validate_indian_plate(self, text: str) -> bool:
        if not text:
            return False
        for pattern in self.patterns:
            if re.match(pattern, text):
                return True
        return False

    def recognize_or_raise(self, plate_image: np.ndarray) -> OCRResult:
        result = self.recognize(plate_image)
        if not result.text:
            raise OCRValidationError("No text detected on license plate")
        return result
