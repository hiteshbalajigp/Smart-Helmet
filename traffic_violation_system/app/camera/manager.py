from __future__ import annotations

import threading
from typing import Callable

import cv2

from app.camera.device import CameraDevice, DiscoveredCamera
from app.config.settings import get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class CameraManager:
    """Detects USB cameras and manages authorized camera devices."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._devices: dict[str, CameraDevice] = {}

    def discover_usb_cameras(self, max_index: int | None = None) -> list[DiscoveredCamera]:
        settings = get_settings()
        limit = max_index if max_index is not None else settings.camera_scan_max_index
        discovered: list[DiscoveredCamera] = []

        for index in range(limit):
            capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            opened = capture.isOpened()
            backend = capture.getBackendName() if opened else "unknown"
            if opened:
                discovered.append(DiscoveredCamera(device_index=index, backend=backend, opened=True))
            capture.release()

        logger.info("Discovered %s USB camera candidate(s).", len(discovered))
        return discovered

    def register_authorized_camera(self, camera_id: str, device_index: int) -> CameraDevice:
        with self._lock:
            device = CameraDevice(device_index=device_index, camera_id=camera_id)
            self._devices[camera_id] = device
            return device

    def get_device(self, camera_id: str) -> CameraDevice | None:
        with self._lock:
            return self._devices.get(camera_id)

    def list_registered(self) -> list[str]:
        with self._lock:
            return list(self._devices.keys())

    def start_camera(
        self,
        camera_id: str,
        frame_handler: Callable[[str, object], None],
        *,
        stop_event: threading.Event | None = None,
    ) -> threading.Thread:
        """Starts an isolated worker thread for one camera."""

        device = self.get_device(camera_id)
        if device is None:
            raise KeyError(f"Camera not registered: {camera_id}")

        thread = threading.Thread(
            target=self._camera_loop,
            name=f"camera-worker-{camera_id}",
            args=(device, frame_handler, stop_event),
            daemon=True,
        )
        thread.start()
        return thread

    def _camera_loop(
        self,
        device: CameraDevice,
        frame_handler: Callable[[str, object], None],
        stop_event: threading.Event | None,
    ) -> None:
        if not device.open():
            logger.error("Camera worker failed to start for %s", device.camera_id)
            return

        logger.info("Camera worker started for %s", device.camera_id)
        try:
            while stop_event is None or not stop_event.is_set():
                ok, frame = device.read_frame()
                if not ok:
                    continue
                try:
                    frame_handler(device.camera_id, frame)
                except Exception:
                    logger.exception("Frame handler error for camera %s", device.camera_id)
        except Exception:
            logger.exception("Camera worker crashed for %s", device.camera_id)
        finally:
            device.close()
            logger.info("Camera worker stopped for %s", device.camera_id)
