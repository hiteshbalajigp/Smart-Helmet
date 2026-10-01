"""WPOD-NET license plate detection interface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config.settings import get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class WPODLoadResult:
    loaded: bool
    message: str
    weights_path: Path


class WPODPlateDetector:
    def __init__(self, weights_path: Path | None = None) -> None:
        settings = get_settings()
        self.weights_path = weights_path or settings.wpod_weights_path
        self._model: Any | None = None

    def load(self) -> WPODLoadResult:
        if not self.weights_path.exists():
            msg = "MODEL WEIGHT NOT YET INTEGRATED"
            logger.warning("%s: %s", msg, self.weights_path)
            return WPODLoadResult(loaded=False, message=msg, weights_path=self.weights_path)

        return WPODLoadResult(
            loaded=False,
            message="WPOD-NET loader scaffold ready; integration pending.",
            weights_path=self.weights_path,
        )

    def detect(self, frame: Any) -> list[dict[str, Any]]:
        raise NotImplementedError("Plate detection will be implemented in a later prompt.")
