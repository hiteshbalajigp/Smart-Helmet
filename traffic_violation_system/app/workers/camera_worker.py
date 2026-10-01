"""Per-camera worker orchestration (isolated from other cameras)."""

from __future__ import annotations

import threading
from typing import Callable

from app.camera.manager import CameraManager
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class CameraWorkerRegistry:
    def __init__(self, manager: CameraManager) -> None:
        self.manager = manager
        self._threads: dict[str, threading.Thread] = {}
        self._stop_events: dict[str, threading.Event] = {}
        self._lock = threading.RLock()

    def start(self, camera_id: str, frame_handler: Callable[[str, object], None]) -> None:
        with self._lock:
            if camera_id in self._threads and self._threads[camera_id].is_alive():
                logger.info("Camera worker already running: %s", camera_id)
                return

            stop_event = threading.Event()
            thread = self.manager.start_camera(camera_id, frame_handler, stop_event=stop_event)
            self._threads[camera_id] = thread
            self._stop_events[camera_id] = stop_event
            logger.info("Registered camera worker for %s", camera_id)

    def stop(self, camera_id: str, timeout: float = 5.0) -> None:
        with self._lock:
            stop_event = self._stop_events.get(camera_id)
            thread = self._threads.get(camera_id)
            if stop_event:
                stop_event.set()
            if thread:
                thread.join(timeout=timeout)
            self._threads.pop(camera_id, None)
            self._stop_events.pop(camera_id, None)

    def stop_all(self, timeout: float = 5.0) -> None:
        with self._lock:
            camera_ids = list(self._threads.keys())
        for camera_id in camera_ids:
            self.stop(camera_id, timeout=timeout)
