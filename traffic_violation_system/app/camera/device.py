from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DiscoveredCamera:
    device_index: int
    backend: str
    opened: bool


class CameraDevice:
    """External USB camera handle (OpenCV VideoCapture abstraction)."""

    def __init__(self, device_index: int, camera_id: str) -> None:
        self.device_index = device_index
        self.camera_id = camera_id
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> bool:
        self.close()
        capture = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            logger.error("Failed to open USB camera index=%s camera_id=%s", self.device_index, self.camera_id)
            return False
        self._capture = capture
        return True

    def read_frame(self) -> tuple[bool, Any]:
        if self._capture is None:
            return False, None
        return self._capture.read()

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    @property
    def is_open(self) -> bool:
        return self._capture is not None and self._capture.isOpened()
