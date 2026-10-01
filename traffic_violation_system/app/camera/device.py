from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

import cv2
import numpy as np

from app.config.settings import get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class CameraStatus(str, Enum):
    INITIALIZING = "INITIALIZING"
    CONNECTED = "CONNECTED"
    STREAMING = "STREAMING"
    DISCONNECTED = "DISCONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


@dataclass(frozen=True)
class FrameMetadata:
    frame_id: int
    timestamp: float
    camera_id: str
    width: int
    height: int
    fps: float


@dataclass(frozen=True)
class DiscoveredCamera:
    device_index: int
    backend: str
    opened: bool
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    connection_status: str = "available"


class CameraDevice:
    """OpenCV-backed USB camera abstraction with recovery handling."""

    def __init__(
        self,
        device_index: int,
        camera_id: str,
        *,
        width: int | None = None,
        height: int | None = None,
        fps: int | float | None = None,
        backend: str | None = None,
        reconnect_enabled: bool | None = None,
        reconnect_delay: float | None = None,
    ) -> None:
        settings = get_settings()
        self.device_index = device_index
        self.camera_id = camera_id
        self.width = width if width is not None else settings.camera_width
        self.height = height if height is not None else settings.camera_height
        self.fps = float(fps if fps is not None else settings.camera_fps)
        self.backend = (backend or settings.camera_backend or "auto").lower()
        self.reconnect_enabled = settings.camera_reconnect_enabled if reconnect_enabled is None else reconnect_enabled
        self.reconnect_delay = settings.camera_reconnect_delay if reconnect_delay is None else reconnect_delay
        self._capture: cv2.VideoCapture | None = None
        self._latest_frame: np.ndarray | None = None
        self._latest_metadata: FrameMetadata | None = None
        self._lock = threading.RLock()
        self._status = CameraStatus.INITIALIZING
        self._frame_id = 0
        self._last_read_time: float = 0.0
        self._read_failures = 0
        self._stop_event = threading.Event()
        self._stream_thread: threading.Thread | None = None

    @staticmethod
    def _resolve_backend(backend: str) -> int:
        normalized = backend.lower()
        if normalized in {"auto", "any", "default"}:
            if sys.platform.startswith("linux"):
                return cv2.CAP_V4L2
            if sys.platform.startswith("win"):
                return cv2.CAP_DSHOW
            return cv2.CAP_ANY
        if normalized in {"v4l2", "linux"}:
            return cv2.CAP_V4L2
        if normalized in {"dshow", "windows"}:
            return cv2.CAP_DSHOW
        return cv2.CAP_ANY

    def open(self) -> bool:
        with self._lock:
            self.close()
            self._status = CameraStatus.INITIALIZING
            capture = cv2.VideoCapture(self.device_index, self._resolve_backend(self.backend))
            if not capture.isOpened():
                capture.release()
                self._status = CameraStatus.ERROR
                logger.error("Failed to open USB camera index=%s camera_id=%s", self.device_index, self.camera_id)
                return False

            capture.set(cv2.CAP_PROP_FRAME_WIDTH, float(self.width))
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self.height))
            capture.set(cv2.CAP_PROP_FPS, float(self.fps))

            self._capture = capture
            self._status = CameraStatus.CONNECTED
            logger.info(
                "Camera %s opened on index=%s backend=%s @ %sx%s %sfps",
                self.camera_id,
                self.device_index,
                self.backend,
                self.width,
                self.height,
                self.fps,
            )
            return True

    def read_frame(self) -> tuple[bool, np.ndarray | None, FrameMetadata | None]:
        if self._capture is None:
            self._status = CameraStatus.DISCONNECTED
            return False, None, None

        ok, frame = self._capture.read()
        if not ok or frame is None:
            self._read_failures += 1
            self._status = CameraStatus.DISCONNECTED
            logger.warning("Camera %s read failed (attempt=%s)", self.camera_id, self._read_failures)
            return False, None, None

        self._read_failures = 0
        self._frame_id += 1
        self._last_read_time = time.time()
        self._latest_frame = frame.copy()
        self._latest_metadata = FrameMetadata(
            frame_id=self._frame_id,
            timestamp=self._last_read_time,
            camera_id=self.camera_id,
            width=int(frame.shape[1]),
            height=int(frame.shape[0]),
            fps=self.fps,
        )
        self._status = CameraStatus.STREAMING
        return True, self._latest_frame, self._latest_metadata

    def get_latest_frame(self) -> tuple[np.ndarray | None, FrameMetadata | None]:
        with self._lock:
            if self._latest_frame is None:
                return None, None
            return self._latest_frame.copy(), self._latest_metadata

    def start_stream(self, frame_handler: Callable[[str, np.ndarray, FrameMetadata], None] | None = None) -> threading.Thread:
        if self._stream_thread is not None and self._stream_thread.is_alive():
            return self._stream_thread

        self._stop_event = threading.Event()
        self._stream_thread = threading.Thread(
            target=self._stream_loop,
            args=(frame_handler,),
            name=f"camera-stream-{self.camera_id}",
            daemon=True,
        )
        self._stream_thread.start()
        return self._stream_thread

    def stop_stream(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._stream_thread is not None and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=timeout)
        self._stream_thread = None
        self.close()

    def _stream_loop(self, frame_handler: Callable[[str, np.ndarray, FrameMetadata], None] | None = None) -> None:
        if not self.open():
            return

        while not self._stop_event.is_set():
            ok, frame, metadata = self.read_frame()
            if not ok:
                if self.reconnect_enabled and self._read_failures > 0:
                    self._status = CameraStatus.RECONNECTING
                    logger.warning("Camera %s disconnected, attempting reconnect in %.1fs", self.camera_id, self.reconnect_delay)
                    self.close()
                    time.sleep(self.reconnect_delay)
                    if not self.open():
                        time.sleep(self.reconnect_delay)
                    continue
                time.sleep(0.1)
                continue

            if frame is not None and metadata is not None and frame_handler is not None:
                try:
                    frame_handler(self.camera_id, frame, metadata)
                except Exception:
                    logger.exception("Frame handler failure for camera %s", self.camera_id)

        self._status = CameraStatus.STOPPED
        self.close()

    def close(self) -> None:
        with self._lock:
            if self._capture is not None:
                self._capture.release()
                self._capture = None
            self._status = CameraStatus.STOPPED if self._stop_event.is_set() else CameraStatus.DISCONNECTED

    @property
    def is_open(self) -> bool:
        return self._capture is not None and self._capture.isOpened()

    @property
    def status(self) -> CameraStatus:
        return self._status

    @property
    def last_read_time(self) -> float:
        return self._last_read_time

    @property
    def read_failures(self) -> int:
        return self._read_failures
