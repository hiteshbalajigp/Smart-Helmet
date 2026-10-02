from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectionBox:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2.0

    def as_xyxy(self) -> tuple[float, float, float, float]:
        return (self.x1, self.y1, self.x2, self.y2)


@dataclass
class DetectionResult:
    class_id: int
    class_name: str
    confidence: float
    bounding_box: DetectionBox
    frame_id: int = 0
    timestamp: float = 0.0
    camera_id: str = "unknown"


@dataclass(frozen=True)
class InferenceMetrics:
    model_name: str
    model_path: str
    device: str
    model_status: str
    confidence_threshold: float
    frame_count: int = 0
    detection_count: int = 0
    inference_fps: float = 0.0
    average_inference_ms: float = 0.0


@dataclass(frozen=True)
class DetectionBatch:
    detections: list[DetectionResult]
    metrics: InferenceMetrics
