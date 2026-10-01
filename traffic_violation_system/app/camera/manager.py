from __future__ import annotations

import threading
import time
from typing import Any, Callable

import cv2

from app.camera.device import CameraDevice, CameraStatus, DiscoveredCamera
from app.config.settings import get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class CameraManager:
    """Detects USB cameras and manages authorized camera devices."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._devices: dict[str, CameraDevice] = {}

    def discover_usb_cameras(
        self,
        max_index: int | None = None,
        backend: str | None = None,
    ) -> list[DiscoveredCamera]:
        settings = get_settings()
        limit = max_index if max_index is not None else settings.camera_scan_max_index
        backend_name = (backend or settings.camera_backend or "auto").lower()
        discovered: list[DiscoveredCamera] = []

        for index in range(limit):
            capture = cv2.VideoCapture(index, CameraDevice._resolve_backend(backend_name))
            opened = capture.isOpened()
            if opened:
                width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
                discovered.append(
                    DiscoveredCamera(
                        device_index=index,
                        backend=backend_name,
                        opened=True,
                        width=width or None,
                        height=height or None,
                        fps=fps or None,
                        connection_status="available",
                    )
                )
            capture.release()

        logger.info("Discovered %s USB camera candidate(s).", len(discovered))
        return discovered

    def register_authorized_camera(
        self,
        camera_id: str,
        device_index: int,
        *,
        camera_path: str | None = None,
        width: int | None = None,
        height: int | None = None,
        fps: int | float | None = None,
        backend: str | None = None,
        reconnect_enabled: bool | None = None,
        reconnect_delay: float | None = None,
    ) -> CameraDevice:
        with self._lock:
            device = CameraDevice(
                device_index=device_index,
                camera_id=camera_id,
                width=width,
                height=height,
                fps=fps,
                backend=backend,
                reconnect_enabled=reconnect_enabled,
                reconnect_delay=reconnect_delay,
            )
            self._devices[camera_id] = device
            if camera_path:
                device.device_path = camera_path  # type: ignore[attr-defined]
            return device

    def get_device(self, camera_id: str) -> CameraDevice | None:
        with self._lock:
            return self._devices.get(camera_id)

    def get_status(self, camera_id: str) -> CameraStatus | None:
        device = self.get_device(camera_id)
        if device is None:
            return None
        return device.status

    def list_registered(self) -> list[str]:
        with self._lock:
            return list(self._devices.keys())

    def start_camera(
        self,
        camera_id: str,
        frame_handler: Callable[[str, Any, Any], None] | None = None,
        *,
        stop_event: threading.Event | None = None,
    ) -> threading.Thread:
        """Starts an isolated worker thread for one camera."""

        device = self.get_device(camera_id)
        if device is None:
            raise KeyError(f"Camera not registered: {camera_id}")

        if stop_event is None:
            stop_event = threading.Event()

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
        frame_handler: Callable[[str, Any, Any], None] | None,
        stop_event: threading.Event,
    ) -> None:
        if not device.open():
            logger.error("Camera worker failed to start for %s", device.camera_id)
            return

        logger.info("Camera worker started for %s", device.camera_id)
        try:
            while not stop_event.is_set():
                ok, frame, metadata = device.read_frame()
                if not ok:
                    if device.reconnect_enabled:
                        logger.warning("Camera %s lost stream; attempting reconnect.", device.camera_id)
                        device.close()
                        time_sleep = getattr(device, "reconnect_delay", 2.0)
                        if time_sleep > 0:
                            stop_event.wait(time_sleep)
                        if not device.open():
                            continue
                    else:
                        stop_event.wait(0.1)
                    continue

                if frame_handler is not None and frame is not None and metadata is not None:
                    try:
                        frame_handler(device.camera_id, frame, metadata)
                    except Exception:
                        logger.exception("Frame handler error for camera %s", device.camera_id)
        except Exception:
            logger.exception("Camera worker crashed for %s", device.camera_id)
        finally:
            device.close()
            device._status = CameraStatus.STOPPED
            logger.info("Camera worker stopped for %s", device.camera_id)

    def stop_camera(self, camera_id: str, timeout: float = 5.0) -> None:
        device = self.get_device(camera_id)
        if device is None:
            return
        device.stop_stream(timeout=timeout)

    def list_camera_status(self) -> dict[str, str]:
        with self._lock:
            return {camera_id: device.status.value for camera_id, device in self._devices.items()}
