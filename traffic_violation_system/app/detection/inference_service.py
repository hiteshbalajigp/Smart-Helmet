from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.camera.frame_provider import LatestFrameProvider
from app.config.settings import get_settings
from app.detection.detection_result import DetectionBatch, DetectionResult, InferenceMetrics
from app.detection.yolo_loader import YOLODetector
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class YOLOv8InferenceService:
    detector: YOLODetector | None = None
    camera_id: str = "helmet-camera"
    confidence_threshold: float | None = None
    iou_threshold: float | None = None
    image_size: int | None = None
    max_detections: int | None = None
    device: str | None = None

    def __post_init__(self) -> None:
        settings = get_settings()
        if self.detector is None:
            self.detector = YOLODetector(
                weights_path=settings.yolo_model_path,
                device=self.device or settings.yolo_device,
                confidence_threshold=self.confidence_threshold if self.confidence_threshold is not None else settings.yolo_confidence_threshold,
                iou_threshold=self.iou_threshold if self.iou_threshold is not None else settings.yolo_iou_threshold,
                image_size=self.image_size if self.image_size is not None else settings.yolo_image_size,
                max_detections=self.max_detections if self.max_detections is not None else settings.yolo_max_detections,
            )

        self._frame_provider = LatestFrameProvider(camera_id=self.camera_id)
        self._frame_count = 0
        self._total_inference_ms = 0.0
        self._last_inference_time = 0.0

    def bind_frame_provider(self, frame_provider: LatestFrameProvider) -> None:
        self._frame_provider = frame_provider

    def process_frame(
        self,
        frame: Any,
        *,
        camera_id: str | None = None,
        frame_id: int = 0,
        timestamp: float | None = None,
    ) -> DetectionBatch:
        detector = self.detector or YOLODetector()
        if timestamp is None:
            timestamp = time.time()
        start = time.perf_counter()

        status = detector.status()
        if not status.loaded:
            load_result = detector.load()
            status = detector.status()

        if status.loaded:
            detections = detector.predict(
                frame,
                confidence_threshold=self.confidence_threshold,
                iou_threshold=self.iou_threshold,
                image_size=self.image_size,
                max_detections=self.max_detections,
            )
            for detection in detections:
                detection.frame_id = frame_id
                detection.timestamp = timestamp
                detection.camera_id = camera_id or self.camera_id
        else:
            logger.info("YOLO model unavailable; returning empty detection set: %s", status.message)
            detections = []

        elapsed = time.perf_counter() - start
        self._frame_count += 1
        self._total_inference_ms += elapsed * 1000.0
        self._last_inference_time = elapsed * 1000.0

        status = detector.status()
        metrics = InferenceMetrics(
            model_name=detector.model_name,
            model_path=str(detector.weights_path),
            device=status.device,
            model_status=status.status.value,
            confidence_threshold=detector.confidence_threshold,
            frame_count=self._frame_count,
            detection_count=len(detections),
            inference_fps=(1.0 / max(elapsed, 1e-6)) if elapsed > 0 else 0.0,
            average_inference_ms=self._total_inference_ms / max(self._frame_count, 1),
        )
        return DetectionBatch(detections=detections, metrics=metrics)

    def process_latest_frame(self, *, camera_id: str | None = None) -> DetectionBatch:
        frame, metadata = self._frame_provider.get_latest()
        if frame is None:
            return DetectionBatch(detections=[], metrics=InferenceMetrics(
                model_name=self.detector.model_name if self.detector else "unknown",
                model_path=str((self.detector.weights_path if self.detector else "")),
                device=(self.detector.device if self.detector else "unknown"),
                model_status="MODEL_NOT_AVAILABLE",
                confidence_threshold=(self.detector.confidence_threshold if self.detector else 0.0),
            ))

        frame_id = metadata.frame_id if metadata is not None else 0
        timestamp = metadata.timestamp if metadata is not None else time.time()
        return self.process_frame(frame, camera_id=camera_id or self.camera_id, frame_id=frame_id, timestamp=timestamp)
