"""PaddleOCR interface for license plate text extraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config.settings import get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class PaddleOCRLoadResult:
    loaded: bool
    message: str


class PaddleOCRService:
    def __init__(self) -> None:
        settings = get_settings()
        self.lang = settings.paddleocr_lang
        self._engine: Any | None = None

    def load(self) -> PaddleOCRLoadResult:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            return PaddleOCRLoadResult(loaded=False, message=f"PaddleOCR not installed: {exc}")

        self._engine = PaddleOCR(use_angle_cls=True, lang=self.lang, show_log=False)
        return PaddleOCRLoadResult(loaded=True, message="PaddleOCR engine initialized")

    def recognize(self, image: Any) -> str:
        raise NotImplementedError("OCR pipeline will be implemented in a later prompt.")
