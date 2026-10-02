from __future__ import annotations

from typing import Iterable

import cv2
import numpy as np

from app.detection.detection_result import DetectionResult


class DetectionVisualizer:
    """Development-only visualization for YOLO results."""

    @staticmethod
    def annotate(
        frame: np.ndarray,
        detections: Iterable[DetectionResult],
        *,
        device: str,
        fps: float,
    ) -> np.ndarray:
        output = frame.copy()
        color_map = {
            "person": (0, 200, 255),
            "motorcycle": (255, 165, 0),
            "helmet": (0, 255, 0),
            "no_helmet": (0, 0, 255),
            "license_plate": (255, 0, 255),
        }

        for det in detections:
            x1, y1, x2, y2 = map(int, det.bounding_box.as_xyxy())
            color = color_map.get(det.class_name, (200, 200, 200))
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
            label = f"{det.class_name} {det.confidence:.2f}"
            cv2.putText(output, label, (x1, max(18, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        cv2.putText(
            output,
            f"YOLOv8 device={device} fps={fps:.1f}",
            (12, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )
        return output
