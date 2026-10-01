"""Geometry and bounding box utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float = 1.0
    class_id: int = -1
    track_id: int | None = None

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    def iou(self, other: "BoundingBox") -> float:
        inter_x1 = max(self.x1, other.x1)
        inter_y1 = max(self.y1, other.y1)
        inter_x2 = min(self.x2, other.x2)
        inter_y2 = min(self.y2, other.y2)
        inter_w = max(0.0, inter_x2 - inter_x1)
        inter_h = max(0.0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h
        union = self.area + other.area - inter_area
        if union <= 0:
            return 0.0
        return inter_area / union

    def contains_point(self, x: float, y: float) -> bool:
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def as_xyxy(self) -> tuple[float, float, float, float]:
        return (self.x1, self.y1, self.x2, self.y2)

    def as_xywh(self) -> tuple[float, float, float, float]:
        return (self.x1, self.y1, self.width, self.height)


def clip_bbox(bbox: BoundingBox, width: int, height: int) -> BoundingBox:
    return BoundingBox(
        x1=max(0.0, min(float(width), bbox.x1)),
        y1=max(0.0, min(float(height), bbox.y1)),
        x2=max(0.0, min(float(width), bbox.x2)),
        y2=max(0.0, min(float(height), bbox.y2)),
        confidence=bbox.confidence,
        class_id=bbox.class_id,
        track_id=bbox.track_id,
    )


def associate_by_iou(
    primary: Sequence[BoundingBox],
    secondary: Sequence[BoundingBox],
    iou_threshold: float,
) -> dict[int, list[BoundingBox]]:
    """Associate secondary boxes to primary boxes by IoU."""
    associations: dict[int, list[BoundingBox]] = {idx: [] for idx in range(len(primary))}
    for sec in secondary:
        best_idx = -1
        best_iou = 0.0
        for idx, pri in enumerate(primary):
            iou = pri.iou(sec)
            if iou >= iou_threshold and iou > best_iou:
                best_iou = iou
                best_idx = idx
        if best_idx >= 0:
            associations[best_idx].append(sec)
    return associations
