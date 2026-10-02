"""YOLOv8 model loading and detection pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from app.config.settings import get_settings
from app.detection.detection_result import DetectionBox, DetectionResult
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class YOLOModelStatus(str, Enum):
    MODEL_NOT_AVAILABLE = "MODEL_NOT_AVAILABLE"
    MODEL_LOADED = "MODEL_LOADED"
    MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"


@dataclass(frozen=True)
class YOLOLoadResult:
    loaded: bool
    message: str
    model_path: Path
    device: str
    status: YOLOModelStatus
    reason: str | None = None


class YOLODetector:
    DEFAULT_CLASS_MAP = {
        0: "person",
        1: "motorcycle",
        2: "helmet",
        3: "no_helmet",
        4: "license_plate",
    }

    def __init__(
        self,
        weights_path: Path | str | None = None,
        *,
        device: str | None = None,
        confidence_threshold: float | None = None,
        iou_threshold: float | None = None,
        image_size: int | None = None,
        max_detections: int | None = None,
        class_map: dict[int, str] | None = None,
    ) -> None:
        settings = get_settings()
        self.weights_path = Path(weights_path) if weights_path is not None else Path(settings.yolo_model_path)
        self.device = (device or settings.yolo_device or "auto").lower()
        self.confidence_threshold = float(confidence_threshold if confidence_threshold is not None else settings.yolo_confidence_threshold)
        self.iou_threshold = float(iou_threshold if iou_threshold is not None else settings.yolo_iou_threshold)
        self.image_size = int(image_size if image_size is not None else settings.yolo_image_size)
        self.max_detections = int(max_detections if max_detections is not None else settings.yolo_max_detections)
        self.class_mapping = {**self.DEFAULT_CLASS_MAP, **(class_map or {})}
        self._model: Any | None = None
        self._runtime_device = self._detect_runtime_device()
        self._model_name = self.weights_path.name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _detect_runtime_device(self) -> str:
        if self.device and self.device != "auto":
            return self.device
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            logger.debug("CUDA unavailable; falling back to CPU for YOLOv8 inference.")
        return "cpu"

    def status(self) -> YOLOLoadResult:
        if self._model is None:
            if not self.weights_path.exists():
                message = f"Model not available at {self.weights_path}"
                return YOLOLoadResult(
                    loaded=False,
                    message=message,
                    model_path=self.weights_path,
                    device=self._runtime_device,
                    status=YOLOModelStatus.MODEL_NOT_AVAILABLE,
                    reason="missing_model",
                )
            return YOLOLoadResult(
                loaded=False,
                message="YOLO model is not loaded",
                model_path=self.weights_path,
                device=self._runtime_device,
                status=YOLOModelStatus.MODEL_NOT_AVAILABLE,
                reason="not_loaded",
            )
        return YOLOLoadResult(
            loaded=True,
            message="YOLO model loaded",
            model_path=self.weights_path,
            device=self._runtime_device,
            status=YOLOModelStatus.MODEL_LOADED,
        )

    def load(self) -> YOLOLoadResult:
        if not self.weights_path.exists():
            message = f"Model path missing: {self.weights_path}"
            logger.warning(message)
            self._model = None
            return YOLOLoadResult(
                loaded=False,
                message=message,
                model_path=self.weights_path,
                device=self._runtime_device,
                status=YOLOModelStatus.MODEL_NOT_AVAILABLE,
                reason="missing_model",
            )

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            message = f"Ultralytics not installed or unavailable: {exc}"
            logger.exception(message)
            self._model = None
            return YOLOLoadResult(
                loaded=False,
                message=message,
                model_path=self.weights_path,
                device=self._runtime_device,
                status=YOLOModelStatus.MODEL_LOAD_FAILED,
                reason=str(exc),
            )

        try:
            self._model = YOLO(str(self.weights_path))
            self._runtime_device = self._detect_runtime_device()
            if self._runtime_device == "cuda":
                logger.info("YOLOv8 model loaded on CUDA device using %s", self.weights_path)
            else:
                logger.info("YOLOv8 model loaded on CPU device using %s", self.weights_path)
            return YOLOLoadResult(
                loaded=True,
                message="YOLOv8 model loaded successfully",
                model_path=self.weights_path,
                device=self._runtime_device,
                status=YOLOModelStatus.MODEL_LOADED,
            )
        except Exception as exc:  # pragma: no cover - defensive path for missing/invalid weights
            logger.exception("Failed to load YOLOv8 model at %s", self.weights_path)
            self._model = None
            return YOLOLoadResult(
                loaded=False,
                message=f"Failed to load YOLOv8 model: {exc}",
                model_path=self.weights_path,
                device=self._runtime_device,
                status=YOLOModelStatus.MODEL_LOAD_FAILED,
                reason=str(exc),
            )

    def resolve_class_name(self, class_id: int | Any) -> str:
        return self.class_mapping.get(int(class_id), f"class_{class_id}")

    def parse_model_output(self, detection_output: Any) -> list[DetectionResult]:
        if detection_output is None:
            return []

        if isinstance(detection_output, (list, tuple)):
            if not detection_output:
                return []
            result = detection_output[0]
        else:
            result = detection_output

        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return []

        detections: list[DetectionResult] = []
        for item in boxes:
            if item is None:
                continue

            xyxy = getattr(item, "xyxy", None)
            conf_values = getattr(item, "conf", None)
            cls_values = getattr(item, "cls", None)
            if xyxy is None or conf_values is None or cls_values is None:
                continue

            coords = xyxy[0] if isinstance(xyxy, list) and len(xyxy) > 0 else xyxy
            if coords is None:
                continue

            try:
                x1, y1, x2, y2 = [float(v) for v in coords[:4]]
            except (TypeError, ValueError):
                continue

            class_id = int(cls_values[0]) if hasattr(cls_values, "__len__") else int(cls_values)
            conf = float(conf_values[0]) if hasattr(conf_values, "__len__") else float(conf_values)
            if conf < self.confidence_threshold:
                continue

            detections.append(
                DetectionResult(
                    class_id=class_id,
                    class_name=self.resolve_class_name(class_id),
                    confidence=conf,
                    bounding_box=DetectionBox(x1=x1, y1=y1, x2=x2, y2=y2),
                )
            )
        return detections

    def predict(
        self,
        frame: Any,
        *,
        confidence_threshold: float | None = None,
        iou_threshold: float | None = None,
        image_size: int | None = None,
        max_detections: int | None = None,
    ) -> list[DetectionResult]:
        if self._model is None:
            load_result = self.load()
            if not load_result.loaded:
                raise RuntimeError(load_result.message)

        conf = self.confidence_threshold if confidence_threshold is None else float(confidence_threshold)
        iou = self.iou_threshold if iou_threshold is None else float(iou_threshold)
        size = self.image_size if image_size is None else int(image_size)
        max_det = self.max_detections if max_detections is None else int(max_detections)

        outputs = self._model(frame, conf=conf, iou=iou, imgsz=size, verbose=False, max_det=max_det)
        return self.parse_model_output(outputs)
