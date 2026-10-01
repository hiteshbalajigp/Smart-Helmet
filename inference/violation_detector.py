"""Traffic violation rule engine with enhanced no-helmet detection."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from inference.tracker import TrackedDetection
from utils.geometry import BoundingBox, associate_by_iou


class ViolationType(str, Enum):
    NO_HELMET = "no_helmet"
    TRIPLE_RIDING = "triple_riding"


@dataclass
class ViolationEvent:
    violation_id: str
    violation_type: ViolationType
    timestamp: datetime
    track_id: int
    motorcycle_bbox: BoundingBox | None
    rider_bboxes: list[BoundingBox] = field(default_factory=list)
    plate_text: str | None = None
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ViolationDetector:
    """Detect riders without helmets on motorcycles and nearby two-wheelers."""

    def __init__(
        self,
        helmet_iou_threshold: float = 0.3,
        rider_motorcycle_iou: float = 0.2,
        triple_riding_threshold: int = 2,
        cooldown_sec: float = 10.0,
        min_confidence: float = 0.5,
        no_helmet_confidence: float = 0.45,
        head_region_ratio: float = 0.35,
        detect_standalone_no_helmet: bool = True,
        require_motorcycle: bool = False,
        no_helmet_only: bool = False,
    ) -> None:
        self.helmet_iou_threshold = helmet_iou_threshold
        self.rider_motorcycle_iou = rider_motorcycle_iou
        self.triple_riding_threshold = triple_riding_threshold
        self.cooldown_sec = cooldown_sec
        self.min_confidence = min_confidence
        self.no_helmet_confidence = no_helmet_confidence
        self.head_region_ratio = head_region_ratio
        self.detect_standalone_no_helmet = detect_standalone_no_helmet
        self.require_motorcycle = require_motorcycle
        self.no_helmet_only = no_helmet_only
        self._last_violation_time: dict[tuple[ViolationType, int], float] = {}

    def process(self, detections: list[TrackedDetection]) -> list[ViolationEvent]:
        motorcycles = [d for d in detections if d.class_name == "motorcycle"]
        persons = [d for d in detections if d.class_name == "person"]
        helmets = [d for d in detections if d.class_name == "helmet"]
        no_helmets = [d for d in detections if d.class_name == "no_helmet"]

        events: list[ViolationEvent] = []
        flagged_tracks: set[int] = set()

        if not self.no_helmet_only:
            events.extend(self._detect_triple_riding(motorcycles, persons))

        events.extend(
            self._detect_no_helmet_on_riders(
                motorcycles=motorcycles,
                persons=persons,
                helmets=helmets,
                no_helmets=no_helmets,
                flagged_tracks=flagged_tracks,
            )
        )

        if self.detect_standalone_no_helmet:
            events.extend(
                self._detect_direct_no_helmet(
                    no_helmets=no_helmets,
                    motorcycles=motorcycles,
                    persons=persons,
                    flagged_tracks=flagged_tracks,
                )
            )

        return events

    def _detect_triple_riding(
        self,
        motorcycles: list[TrackedDetection],
        persons: list[TrackedDetection],
    ) -> list[ViolationEvent]:
        events: list[ViolationEvent] = []
        moto_boxes = [m.bbox for m in motorcycles]
        person_boxes = [p.bbox for p in persons]
        moto_to_riders = associate_by_iou(moto_boxes, person_boxes, self.rider_motorcycle_iou)

        for moto_idx, moto in enumerate(motorcycles):
            riders = moto_to_riders.get(moto_idx, [])
            if len(riders) > self.triple_riding_threshold:
                event = self._create_event(
                    ViolationType.TRIPLE_RIDING,
                    moto.track_id,
                    moto.bbox,
                    riders,
                    confidence=moto.bbox.confidence,
                )
                if event:
                    events.append(event)
        return events

    def _detect_no_helmet_on_riders(
        self,
        motorcycles: list[TrackedDetection],
        persons: list[TrackedDetection],
        helmets: list[TrackedDetection],
        no_helmets: list[TrackedDetection],
        flagged_tracks: set[int],
    ) -> list[ViolationEvent]:
        events: list[ViolationEvent] = []
        rider_candidates = self._collect_riders(motorcycles, persons)

        for rider_det, moto_det in rider_candidates:
            rider_box = rider_det.bbox
            if rider_box.confidence < self.min_confidence:
                continue

            head = self._head_region(rider_box)
            has_helmet = self._head_has_helmet(head, helmets)
            has_no_helmet = self._head_has_no_helmet(head, no_helmets, rider_box)

            if not has_no_helmet and not has_helmet:
                # No head label visible: treat as violation only if no_helmet model is uncertain
                continue

            if has_no_helmet or not has_helmet:
                track_id = rider_det.track_id
                if track_id in flagged_tracks:
                    continue
                moto_bbox = moto_det.bbox if moto_det else None
                parent_track = moto_det.track_id if moto_det else track_id
                confidence = max(
                    rider_box.confidence,
                    max((nh.bbox.confidence for nh in no_helmets if head.iou(nh.bbox) >= self.helmet_iou_threshold), default=0.0),
                )
                event = self._create_event(
                    ViolationType.NO_HELMET,
                    parent_track,
                    moto_bbox or rider_box,
                    [rider_box],
                    confidence=confidence,
                    rider_track_id=track_id,
                )
                if event:
                    flagged_tracks.add(track_id)
                    events.append(event)

        return events

    def _detect_direct_no_helmet(
        self,
        no_helmets: list[TrackedDetection],
        motorcycles: list[TrackedDetection],
        persons: list[TrackedDetection],
        flagged_tracks: set[int],
    ) -> list[ViolationEvent]:
        """Flag high-confidence no_helmet detections even without a person label."""
        events: list[ViolationEvent] = []

        for nh in no_helmets:
            if nh.bbox.confidence < self.no_helmet_confidence:
                continue
            if nh.track_id in flagged_tracks:
                continue

            linked_person = self._nearest_person(nh.bbox, persons)
            linked_moto = self._nearest_motorcycle(nh.bbox, motorcycles)
            if self.require_motorcycle and linked_moto is None:
                continue

            track_id = linked_person.track_id if linked_person else nh.track_id
            if track_id in flagged_tracks:
                continue

            moto_bbox = linked_moto.bbox if linked_moto else None
            parent_track = linked_moto.track_id if linked_moto else track_id
            rider_boxes = [linked_person.bbox] if linked_person else [nh.bbox]

            event = self._create_event(
                ViolationType.NO_HELMET,
                parent_track,
                moto_bbox or nh.bbox,
                rider_boxes,
                confidence=nh.bbox.confidence,
                rider_track_id=track_id,
            )
            if event:
                flagged_tracks.add(track_id)
                events.append(event)

        return events

    def _collect_riders(
        self,
        motorcycles: list[TrackedDetection],
        persons: list[TrackedDetection],
    ) -> list[tuple[TrackedDetection, TrackedDetection | None]]:
        """Return rider detections paired with their motorcycle when available."""
        results: list[tuple[TrackedDetection, TrackedDetection | None]] = []
        assigned_persons: set[int] = set()

        if motorcycles:
            moto_boxes = [m.bbox for m in motorcycles]
            person_boxes = [p.bbox for p in persons]
            moto_to_riders = associate_by_iou(moto_boxes, person_boxes, self.rider_motorcycle_iou)
            for moto_idx, moto in enumerate(motorcycles):
                for rider_box in moto_to_riders.get(moto_idx, []):
                    rider_det = self._find_detection_for_bbox(persons, rider_box)
                    if rider_det and rider_det.track_id not in assigned_persons:
                        results.append((rider_det, moto))
                        assigned_persons.add(rider_det.track_id)

        if not self.require_motorcycle:
            for person in persons:
                if person.track_id not in assigned_persons:
                    results.append((person, None))

        return results

    @staticmethod
    def _find_detection_for_bbox(
        detections: list[TrackedDetection],
        bbox: BoundingBox,
    ) -> TrackedDetection | None:
        for det in detections:
            if det.bbox.iou(bbox) >= 0.5:
                return det
        return None

    def _head_region(self, rider_box: BoundingBox) -> BoundingBox:
        head_height = rider_box.height * self.head_region_ratio
        return BoundingBox(
            x1=rider_box.x1,
            y1=rider_box.y1,
            x2=rider_box.x2,
            y2=rider_box.y1 + head_height,
            confidence=rider_box.confidence,
            class_id=rider_box.class_id,
            track_id=rider_box.track_id,
        )

    def _head_has_helmet(self, head: BoundingBox, helmets: list[TrackedDetection]) -> bool:
        return any(head.iou(h.bbox) >= self.helmet_iou_threshold for h in helmets)

    def _head_has_no_helmet(
        self,
        head: BoundingBox,
        no_helmets: list[TrackedDetection],
        rider_box: BoundingBox,
    ) -> bool:
        for nh in no_helmets:
            if nh.bbox.confidence < self.no_helmet_confidence:
                continue
            if head.iou(nh.bbox) >= self.helmet_iou_threshold:
                return True
            if rider_box.iou(nh.bbox) >= self.helmet_iou_threshold:
                return True
        return False

    @staticmethod
    def _nearest_person(
        bbox: BoundingBox,
        persons: list[TrackedDetection],
    ) -> TrackedDetection | None:
        best: TrackedDetection | None = None
        best_iou = 0.0
        for person in persons:
            iou = bbox.iou(person.bbox)
            if iou > best_iou:
                best_iou = iou
                best = person
        return best if best_iou >= 0.05 else None

    @staticmethod
    def _nearest_motorcycle(
        bbox: BoundingBox,
        motorcycles: list[TrackedDetection],
    ) -> TrackedDetection | None:
        best: TrackedDetection | None = None
        best_iou = 0.0
        for moto in motorcycles:
            iou = bbox.iou(moto.bbox)
            if iou > best_iou:
                best_iou = iou
                best = moto
        return best if best_iou >= 0.05 else None

    def _create_event(
        self,
        violation_type: ViolationType,
        track_id: int,
        motorcycle_bbox: BoundingBox | None,
        rider_bboxes: list[BoundingBox],
        confidence: float,
        rider_track_id: int | None = None,
    ) -> ViolationEvent | None:
        dedupe_track = rider_track_id if violation_type == ViolationType.NO_HELMET else track_id
        key = (violation_type, dedupe_track)
        now = time.time()
        last = self._last_violation_time.get(key, 0.0)
        if now - last < self.cooldown_sec:
            return None
        self._last_violation_time[key] = now

        return ViolationEvent(
            violation_id=str(uuid.uuid4()),
            violation_type=violation_type,
            timestamp=datetime.now(timezone.utc),
            track_id=track_id,
            motorcycle_bbox=motorcycle_bbox,
            rider_bboxes=rider_bboxes,
            confidence=confidence,
        )
