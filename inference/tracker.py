"""Multi-object tracking wrapper using ByteTrack via Ultralytics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from ultralytics import YOLO

from utils.geometry import BoundingBox


@dataclass
class TrackedDetection:
    bbox: BoundingBox
    class_name: str
    track_id: int


CLASS_ID_TO_NAME = {
    0: "person",
    1: "motorcycle",
    2: "helmet",
    3: "no_helmet",
    4: "license_plate",
}


class YOLOTracker:
    """YOLOv8 detection with built-in ByteTrack tracking."""

    def __init__(
        self,
        model_path: str,
        confidence: float = 0.45,
        iou: float = 0.5,
        tracker: str = "bytetrack.yaml",
        device: str = "auto",
    ) -> None:
        self.model = YOLO(model_path)
        self.confidence = confidence
        self.iou = iou
        self.tracker = tracker
        self.device = device

    def track(self, frame: np.ndarray) -> list[TrackedDetection]:
        results = self.model.track(
            source=frame,
            persist=True,
            conf=self.confidence,
            iou=self.iou,
            tracker=self.tracker,
            device=self.device,
            verbose=False,
        )
        detections: list[TrackedDetection] = []
        if not results:
            return detections

        result = results[0]
        if result.boxes is None:
            return detections

        boxes = result.boxes
        for idx in range(len(boxes)):
            xyxy = boxes.xyxy[idx].cpu().numpy()
            cls_id = int(boxes.cls[idx].cpu().numpy())
            conf = float(boxes.conf[idx].cpu().numpy())
            track_id = None
            if boxes.id is not None:
                track_id = int(boxes.id[idx].cpu().numpy())
            bbox = BoundingBox(
                x1=float(xyxy[0]),
                y1=float(xyxy[1]),
                x2=float(xyxy[2]),
                y2=float(xyxy[3]),
                confidence=conf,
                class_id=cls_id,
                track_id=track_id,
            )
            class_name = CLASS_ID_TO_NAME.get(cls_id, "unknown")
            detections.append(
                TrackedDetection(
                    bbox=bbox,
                    class_name=class_name,
                    track_id=track_id or -(idx + 1),
                )
            )
        return detections
