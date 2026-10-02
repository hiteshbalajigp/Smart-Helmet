from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.detection.detection_result import DetectionBox


class TrackStatus(StrEnum):
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    TEMPORARILY_MISSING = "TEMPORARILY_MISSING"
    LOST = "LOST"
    REMOVED = "REMOVED"


class PersonRole(StrEnum):
    RIDER = "RIDER"
    PILLION = "PILLION"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ObjectTrack:
    track_id: int
    class_name: str
    bounding_box: DetectionBox
    confidence: float
    first_seen: float
    last_seen: float
    age: int
    missed_frames: int
    status: TrackStatus
    velocity_x: float = 0.0
    velocity_y: float = 0.0


@dataclass(frozen=True)
class VehicleTrack(ObjectTrack):
    pass


@dataclass(frozen=True)
class PersonTrack(ObjectTrack):
    pass


@dataclass(frozen=True)
class PersonAssociation:
    person_track_id: int
    bounding_box: DetectionBox
    relative_x: float
    relative_y: float
    association_score: float
    role: PersonRole = PersonRole.UNKNOWN


@dataclass(frozen=True)
class VehiclePersonAssociation:
    vehicle_track_id: int
    person_track_ids: tuple[int, ...]
    persons: tuple[PersonAssociation, ...]
    candidate_rider_track_id: int | None
    candidate_pillion_track_ids: tuple[int, ...]
    unknown_track_ids: tuple[int, ...]
    association_confidence: float
    role_confidence: float

    @property
    def rider_track_id(self) -> int | None:
        return self.candidate_rider_track_id

    @property
    def pillion_track_ids(self) -> tuple[int, ...]:
        return self.candidate_pillion_track_ids

    @property
    def associated_person_count(self) -> int:
        return len(self.person_track_ids)


@dataclass(frozen=True)
class TrackingMetrics:
    active_vehicle_tracks: int = 0
    active_person_tracks: int = 0
    total_tracks_created: int = 0
    tracks_removed: int = 0
    current_associations: int = 0
    association_failures: int = 0
    average_tracking_duration_seconds: float = 0.0


@dataclass(frozen=True)
class SceneTrackingResult:
    frame_id: int
    timestamp: float
    camera_id: str
    vehicle_tracks: tuple[VehicleTrack, ...]
    person_tracks: tuple[PersonTrack, ...]
    associations: tuple[VehiclePersonAssociation, ...]
    metrics: TrackingMetrics
    removed_tracks: tuple[ObjectTrack, ...] = ()
