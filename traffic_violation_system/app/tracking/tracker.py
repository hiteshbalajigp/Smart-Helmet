from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol

from app.detection.detection_result import DetectionBox, DetectionResult
from app.tracking.models import ObjectTrack, PersonTrack, TrackStatus, VehicleTrack
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ObjectTracker(Protocol):
    @property
    def metrics(self) -> Mapping[str, int | float]:
        """Return lightweight lifetime and track-count metrics."""
        ...

    def update(
        self,
        detections: Iterable[DetectionResult],
        *,
        frame_id: int | None = None,
        timestamp: float | None = None,
        camera_id: str | None = None,
    ) -> tuple[tuple[VehicleTrack, ...], tuple[PersonTrack, ...], tuple[ObjectTrack, ...]]:
        """Update identities and return active vehicle, person, and removed tracks."""
        ...


@dataclass
class _TrackState:
    track_id: int
    class_name: str
    is_person: bool
    bounding_box: DetectionBox
    confidence: float
    first_seen: float
    last_seen: float
    age: int
    missed_frames: int
    status: TrackStatus
    velocity_x: float = 0.0
    velocity_y: float = 0.0

    def snapshot(self) -> ObjectTrack:
        track_type = PersonTrack if self.is_person else VehicleTrack
        return track_type(
            track_id=self.track_id,
            class_name=self.class_name,
            bounding_box=self.bounding_box,
            confidence=self.confidence,
            first_seen=self.first_seen,
            last_seen=self.last_seen,
            age=self.age,
            missed_frames=self.missed_frames,
            status=self.status,
            velocity_x=self.velocity_x,
            velocity_y=self.velocity_y,
        )


class IoUObjectTracker:
    """Deterministic class-aware tracker with bounded missed-track retention."""

    def __init__(
        self,
        *,
        person_classes: Iterable[str] = ("person",),
        vehicle_classes: Iterable[str] = ("motorcycle", "motorbike", "two-wheeler", "two_wheeler"),
        max_missed_frames: int = 5,
        min_confidence: float = 0.25,
        match_threshold: float = 0.3,
    ) -> None:
        if max_missed_frames < 0:
            raise ValueError("max_missed_frames must be non-negative")
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")
        if not 0.0 <= match_threshold <= 1.0:
            raise ValueError("match_threshold must be between 0 and 1")

        self.person_classes = self._normalize_classes(person_classes)
        self.vehicle_classes = self._normalize_classes(vehicle_classes)
        if not self.person_classes or not self.vehicle_classes:
            raise ValueError("person_classes and vehicle_classes must not be empty")
        if self.person_classes & self.vehicle_classes:
            raise ValueError("person_classes and vehicle_classes must be distinct")

        self.max_missed_frames = max_missed_frames
        self.min_confidence = min_confidence
        self.match_threshold = match_threshold
        self._tracks: dict[int, _TrackState] = {}
        self._next_track_id = 1
        self._last_frame_id: int | None = None
        self._total_tracks_created = 0
        self._tracks_removed = 0
        self._total_tracking_duration = 0.0

        logger.info("IoU object tracker initialized.")

    @staticmethod
    def _normalize_classes(classes: Iterable[str]) -> set[str]:
        return {name.strip().lower() for name in classes if name.strip()}

    @staticmethod
    def _validate_detection(detection: DetectionResult) -> None:
        if not isinstance(detection, DetectionResult):
            raise ValueError("detections must contain DetectionResult instances")
        box = detection.bounding_box
        if not isinstance(box, DetectionBox):
            raise ValueError("detection bounding_box must be a DetectionBox")
        try:
            values = (box.x1, box.y1, box.x2, box.y2, detection.confidence, detection.timestamp)
            finite_values = all(math.isfinite(value) for value in values)
        except TypeError as error:
            raise ValueError("detection coordinates, confidence, and timestamp must be numeric") from error
        if not finite_values:
            raise ValueError("detection coordinates and confidence must be finite")
        if box.x2 <= box.x1 or box.y2 <= box.y1:
            raise ValueError("detection bounding boxes must have positive area")
        if not 0.0 <= detection.confidence <= 1.0:
            raise ValueError("detection confidence must be between 0 and 1")
        if not isinstance(detection.class_name, str) or not detection.class_name.strip():
            raise ValueError("detection class_name must not be empty")

    @staticmethod
    def _iou(left: DetectionBox, right: DetectionBox) -> float:
        x1 = max(left.x1, right.x1)
        y1 = max(left.y1, right.y1)
        x2 = min(left.x2, right.x2)
        y2 = min(left.y2, right.y2)
        intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        union = left.width * left.height + right.width * right.height - intersection
        return intersection / union if union > 0 else 0.0

    @classmethod
    def _match_score(cls, track: _TrackState, detection: DetectionResult) -> float:
        previous = track.bounding_box
        current = detection.bounding_box
        overlap = cls._iou(previous, current)
        diagonal = max(math.hypot(previous.width, previous.height), 1.0)
        distance = math.hypot(previous.center_x - current.center_x, previous.center_y - current.center_y)
        proximity = max(0.0, 1.0 - distance / (2.0 * diagonal))
        return 0.7 * overlap + 0.3 * proximity

    @classmethod
    def _deduplicate(cls, detections: list[DetectionResult]) -> list[DetectionResult]:
        accepted: list[DetectionResult] = []
        for detection in sorted(detections, key=lambda item: item.confidence, reverse=True):
            if any(
                detection.class_name.strip().lower() == existing.class_name.strip().lower()
                and cls._iou(detection.bounding_box, existing.bounding_box) >= 0.8
                for existing in accepted
            ):
                continue
            accepted.append(detection)
        return accepted

    def update(
        self,
        detections: Iterable[DetectionResult],
        *,
        frame_id: int | None = None,
        timestamp: float | None = None,
        camera_id: str | None = None,
    ) -> tuple[tuple[VehicleTrack, ...], tuple[PersonTrack, ...], tuple[ObjectTrack, ...]]:
        del camera_id
        detection_list = list(detections)
        for detection in detection_list:
            self._validate_detection(detection)

        if frame_id is not None and (not isinstance(frame_id, int) or isinstance(frame_id, bool)):
            raise ValueError("frame_id must be an integer")
        if timestamp is not None and not math.isfinite(timestamp):
            raise ValueError("timestamp must be finite")
        if frame_id is not None:
            if self._last_frame_id is not None and frame_id <= self._last_frame_id:
                raise ValueError("frame_id must increase for every tracker update")
            self._last_frame_id = frame_id

        relevant_classes = self.person_classes | self.vehicle_classes
        tracked_detections = self._deduplicate(
            [
                detection
                for detection in detection_list
                if detection.class_name.strip().lower() in relevant_classes
                and detection.confidence >= self.min_confidence
            ]
        )
        now = timestamp if timestamp is not None else 0.0

        candidates: list[tuple[float, int, int]] = []
        track_ids = sorted(self._tracks)
        for track_id in track_ids:
            track = self._tracks[track_id]
            for detection_index, detection in enumerate(tracked_detections):
                if track.class_name != detection.class_name.strip().lower():
                    continue
                score = self._match_score(track, detection)
                if score >= self.match_threshold:
                    candidates.append((score, track_id, detection_index))
        candidates.sort(reverse=True)

        matched_tracks: set[int] = set()
        matched_detections: set[int] = set()
        for _, track_id, detection_index in candidates:
            if track_id in matched_tracks or detection_index in matched_detections:
                continue
            track = self._tracks[track_id]
            detection = tracked_detections[detection_index]
            elapsed_frames = track.missed_frames + 1
            track.velocity_x = (
                detection.bounding_box.center_x - track.bounding_box.center_x
            ) / elapsed_frames
            track.velocity_y = (
                detection.bounding_box.center_y - track.bounding_box.center_y
            ) / elapsed_frames
            track.bounding_box = detection.bounding_box
            track.confidence = detection.confidence
            track.last_seen = detection.timestamp if detection.timestamp else now
            track.age += 1
            track.missed_frames = 0
            track.status = TrackStatus.ACTIVE
            matched_tracks.add(track_id)
            matched_detections.add(detection_index)

        removed: list[ObjectTrack] = []
        for track_id in list(self._tracks):
            if track_id in matched_tracks:
                continue
            track = self._tracks[track_id]
            track.age += 1
            track.missed_frames += 1
            if track.missed_frames > self.max_missed_frames:
                track.status = TrackStatus.REMOVED
                removed.append(track.snapshot())
                self._tracks_removed += 1
                self._total_tracking_duration += max(0.0, track.last_seen - track.first_seen)
                logger.info("Track removed: track_id=%s class=%s", track_id, track.class_name)
                del self._tracks[track_id]
            elif track.missed_frames == self.max_missed_frames and self.max_missed_frames > 0:
                track.status = TrackStatus.LOST
                logger.info("Track lost: track_id=%s class=%s", track_id, track.class_name)
            else:
                track.status = TrackStatus.TEMPORARILY_MISSING

        for detection_index, detection in enumerate(tracked_detections):
            if detection_index in matched_detections:
                continue
            class_name = detection.class_name.strip().lower()
            first_seen = detection.timestamp if detection.timestamp else now
            track = _TrackState(
                track_id=self._next_track_id,
                class_name=class_name,
                is_person=class_name in self.person_classes,
                bounding_box=detection.bounding_box,
                confidence=detection.confidence,
                first_seen=first_seen,
                last_seen=first_seen,
                age=1,
                missed_frames=0,
                status=TrackStatus.NEW,
            )
            self._tracks[track.track_id] = track
            logger.info("Track created: track_id=%s class=%s", track.track_id, class_name)
            self._next_track_id += 1
            self._total_tracks_created += 1

        active = [
            track.snapshot()
            for track in self._tracks.values()
            if track.status != TrackStatus.LOST
        ]
        vehicles = tuple(track for track in active if track.class_name in self.vehicle_classes)
        people = tuple(track for track in active if track.class_name in self.person_classes)
        return vehicles, people, tuple(removed)

    @property
    def metrics(self) -> Mapping[str, int | float]:
        active_duration = sum(
            max(0.0, track.last_seen - track.first_seen)
            for track in self._tracks.values()
        )
        tracked_count = self._tracks_removed + len(self._tracks)
        return {
            "total_tracks_created": self._total_tracks_created,
            "tracks_removed": self._tracks_removed,
            "average_tracking_duration_seconds": (
                self._total_tracking_duration + active_duration
            )
            / max(tracked_count, 1),
        }
