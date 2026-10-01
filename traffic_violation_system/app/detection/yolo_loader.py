"""YOLOv8 model loading interface (weights integrated in later steps)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config.settings import get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class YOLOLoadResult:
    loaded: bool
    message: str
    weights_path: Path


class YOLODetector:
    def __init__(self, weights_path: Path | None = None) -> None:
        settings = get_settings()
        self.weights_path = weights_path or settings.yolo_weights_path
        self._model: Any | None = None

    def load(self) -> YOLOLoadResult:
        if not self.weights_path.exists():
            msg = "MODEL WEIGHT NOT YET INTEGRATED"
            logger.warning("%s: %s", msg, self.weights_path)
            return YOLOLoadResult(loaded=False, message=msg, weights_path=self.weights_path)

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            return YOLOLoadResult(
                loaded=False,
                message=f"Ultralytics not installed: {exc}",
                weights_path=self.weights_path,
            )

        self._model = YOLO(str(self.weights_path))
        return YOLOLoadResult(loaded=True, message="YOLO model loaded", weights_path=self.weights_path)

    def predict(self, frame: Any) -> list[dict[str, Any]]:
        if self._model is None:
            raise RuntimeError("YOLO model is not loaded")
        raise NotImplementedError("Real-time detection pipeline will be implemented in a later prompt.")
