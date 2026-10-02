from __future__ import annotations

import math
import time
from collections.abc import Iterable

from app.config.settings import Settings, get_settings
from app.detection.detection_result import DetectionBatch, DetectionResult
from app.tracking.association import VehiclePersonAssociator
from app.tracking.models import SceneTrackingResult, TrackingMetrics
from app.tracking.role_assignment import RiderPillionRoleAssigner
from app.tracking.tracker import IoUObjectTracker, ObjectTracker


class VehiclePersonTrackingService:
    def __init__(
        self,
        *,
        tracker: ObjectTracker | None = None,
        settings: Settings | None = None,
    ) -> None:
        settings = settings or get_settings()
        self.enabled = settings.tracking_enabled
        self.association_enabled = settings.association_enabled
        self.camera_id = settings.camera_id
        self.tracker = tracker or IoUObjectTracker(
            person_classes=self._split_classes(settings.tracking_person_classes),
            vehicle_classes=self._split_classes(settings.tracking_vehicle_classes),
            max_missed_frames=settings.track_max_missed_frames,
            min_confidence=settings.track_min_confidence,
            match_threshold=settings.track_match_threshold,
        )
        self.associator = VehiclePersonAssociator(threshold=settings.association_threshold)
        self.role_assigner = RiderPillionRoleAssigner(
            confidence_threshold=settings.role_assignment_threshold,
        )
        self._frame_id = 0

    @staticmethod
    def _split_classes(value: str) -> tuple[str, ...]:
        return tuple(name.strip() for name in value.split(",") if name.strip())

    def process(
        self,
        detections: DetectionBatch | Iterable[DetectionResult],
        *,
        frame_id: int | None = None,
        timestamp: float | None = None,
        camera_id: str | None = None,
    ) -> SceneTrackingResult:
        if isinstance(detections, DetectionBatch):
            items = detections.detections
        else:
            items = list(detections)

        if any(not isinstance(item, DetectionResult) for item in items):
            raise ValueError("detections must contain DetectionResult instances")

        if items:
            first = items[0]
            frame_id = frame_id if frame_id is not None else first.frame_id
            timestamp = timestamp if timestamp is not None else first.timestamp
            camera_id = camera_id or first.camera_id
            if any(item.frame_id != frame_id for item in items):
                raise ValueError("all detections in a batch must have the same frame_id")
            if any(item.camera_id != camera_id for item in items):
                raise ValueError("all detections in a batch must have the same camera_id")

        self._frame_id = frame_id if frame_id is not None else self._frame_id + 1
        if timestamp is not None and not math.isfinite(timestamp):
            raise ValueError("timestamp must be finite")
        current_timestamp = timestamp if timestamp is not None else time.time()
        current_camera_id = camera_id or self.camera_id

        if not self.enabled:
            return SceneTrackingResult(
                frame_id=self._frame_id,
                timestamp=current_timestamp,
                camera_id=current_camera_id,
                vehicle_tracks=(),
                person_tracks=(),
                associations=(),
                metrics=TrackingMetrics(),
            )

        vehicles, people, removed = self.tracker.update(
            items,
            frame_id=self._frame_id,
            timestamp=current_timestamp,
            camera_id=current_camera_id,
        )
        associations = self.associator.associate(vehicles, people) if self.association_enabled else ()
        associations = self.role_assigner.assign(associations, vehicles)
        tracker_metrics = self.tracker.metrics
        metrics = TrackingMetrics(
            active_vehicle_tracks=len(vehicles),
            active_person_tracks=len(people),
            total_tracks_created=int(tracker_metrics.get("total_tracks_created", 0)),
            tracks_removed=int(tracker_metrics.get("tracks_removed", 0)),
            current_associations=sum(bool(item.person_track_ids) for item in associations),
            association_failures=self.associator.association_failures,
            average_tracking_duration_seconds=float(
                tracker_metrics.get("average_tracking_duration_seconds", 0.0)
            ),
        )
        return SceneTrackingResult(
            frame_id=self._frame_id,
            timestamp=current_timestamp,
            camera_id=current_camera_id,
            vehicle_tracks=vehicles,
            person_tracks=people,
            associations=associations,
            metrics=metrics,
            removed_tracks=removed,
        )
