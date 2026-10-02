from __future__ import annotations

import math

import pytest

from app.config.settings import Settings
from app.detection.detection_result import DetectionBatch, DetectionBox, DetectionResult, InferenceMetrics
from app.tracking import (
    IoUObjectTracker,
    PersonRole,
    TrackStatus,
    VehiclePersonTrackingService,
)


def detection(
    class_name: str,
    box: tuple[float, float, float, float],
    *,
    confidence: float = 0.95,
    frame_id: int = 1,
    timestamp: float = 100.0,
    camera_id: str = "test-camera",
) -> DetectionResult:
    return DetectionResult(
        class_id=0,
        class_name=class_name,
        confidence=confidence,
        bounding_box=DetectionBox(*box),
        frame_id=frame_id,
        timestamp=timestamp,
        camera_id=camera_id,
    )


def service(**overrides: object) -> VehiclePersonTrackingService:
    return VehiclePersonTrackingService(settings=Settings(**overrides))


def vehicle(
    x: float = 100,
    *,
    frame_id: int = 1,
    confidence: float = 0.95,
) -> DetectionResult:
    return detection("motorcycle", (x, 100, x + 200, 250), frame_id=frame_id, confidence=confidence)


def person(
    x: float = 150,
    *,
    frame_id: int = 1,
    y: float = 20,
    confidence: float = 0.95,
) -> DetectionResult:
    return detection(
        "person",
        (x, y, x + 45, y + 120),
        frame_id=frame_id,
        confidence=confidence,
    )


def test_single_vehicle_and_person_are_tracked_and_associated() -> None:
    result = service().process([vehicle(), person()])
    assert len(result.vehicle_tracks) == 1
    assert len(result.person_tracks) == 1
    assert result.associations[0].associated_person_count == 1


def test_single_vehicle_can_have_two_associated_people() -> None:
    result = service().process([vehicle(), person(125), person(220)])
    assert result.associations[0].associated_person_count == 2


def test_multiple_vehicles_and_people_form_separate_groups() -> None:
    result = service().process(
        [
            vehicle(100),
            vehicle(450),
            person(140),
            person(230),
            person(490),
        ]
    )
    assert [item.associated_person_count for item in result.associations] == [2, 1]


def test_person_is_associated_with_spatially_corresponding_vehicle() -> None:
    result = service().process([vehicle(100), vehicle(450), person(140)])
    assert result.associations[0].vehicle_track_id == result.vehicle_tracks[0].track_id
    assert result.associations[0].person_track_ids == (result.person_tracks[0].track_id,)
    assert result.associations[1].person_track_ids == ()


def test_person_outside_vehicle_is_not_associated() -> None:
    result = service().process([vehicle(), person(700)])
    assert result.associations[0].person_track_ids == ()
    assert result.metrics.association_failures == 1


def test_vehicle_track_id_persists_across_frames() -> None:
    tracker = IoUObjectTracker()
    first, _, _ = tracker.update([vehicle(frame_id=1)], frame_id=1, timestamp=1.0)
    second, _, _ = tracker.update([vehicle(105, frame_id=2)], frame_id=2, timestamp=2.0)
    assert first[0].track_id == second[0].track_id


def test_person_track_id_persists_across_frames() -> None:
    tracker = IoUObjectTracker()
    _, first, _ = tracker.update([person(frame_id=1)], frame_id=1, timestamp=1.0)
    _, second, _ = tracker.update([person(155, frame_id=2)], frame_id=2, timestamp=2.0)
    assert first[0].track_id == second[0].track_id


def test_temporary_detection_loss_keeps_identity() -> None:
    tracker = IoUObjectTracker(max_missed_frames=2)
    _, first_people, _ = tracker.update([person()], frame_id=1, timestamp=1.0)
    _, missing_people, _ = tracker.update([], frame_id=2, timestamp=2.0)
    _, returned_people, _ = tracker.update([person(frame_id=3)], frame_id=3, timestamp=3.0)
    assert missing_people[0].status == TrackStatus.TEMPORARILY_MISSING
    assert returned_people[0].track_id == first_people[0].track_id


def test_track_is_removed_after_missed_frame_limit() -> None:
    tracker = IoUObjectTracker(max_missed_frames=1)
    _, first_people, _ = tracker.update([person()], frame_id=1, timestamp=1.0)
    _, _, removed = tracker.update([], frame_id=2, timestamp=2.0)
    assert removed == ()
    _, _, removed = tracker.update([], frame_id=3, timestamp=3.0)
    assert removed[0].track_id == first_people[0].track_id
    assert removed[0].status == TrackStatus.REMOVED


def test_multiple_vehicle_associations_remain_separate() -> None:
    result = service().process(
        [vehicle(100), vehicle(450), person(140), person(500)]
    )
    groups = {association.vehicle_track_id: association.person_track_ids for association in result.associations}
    assert len(groups) == 2
    assert all(len(person_ids) == 1 for person_ids in groups.values())
    assert len(set(next(iter(groups.values()))).intersection(set(list(groups.values())[1]))) == 0


def test_association_confidence_is_bounded_and_calculated() -> None:
    result = service().process([vehicle(), person()])
    confidence = result.associations[0].association_confidence
    assert 0.45 <= confidence <= 1.0
    assert math.isfinite(confidence)


def test_single_associated_person_is_a_rider_candidate() -> None:
    association = service().process([vehicle(), person()]).associations[0]
    assert association.candidate_rider_track_id == association.person_track_ids[0]
    assert association.persons[0].role == PersonRole.RIDER


def test_motion_identifies_rider_and_pillion_candidates() -> None:
    processor = service()
    processor.process([vehicle(), person(125), person(220)], frame_id=1, timestamp=1.0)
    result = processor.process(
        [vehicle(110, frame_id=2), person(135, frame_id=2), person(230, frame_id=2)],
        frame_id=2,
        timestamp=2.0,
    )
    association = result.associations[0]
    assert association.candidate_rider_track_id == association.person_track_ids[1]
    assert association.candidate_pillion_track_ids == (association.person_track_ids[0],)


def test_ambiguous_multi_person_roles_remain_unknown() -> None:
    association = service().process([vehicle(), person(125), person(220)]).associations[0]
    assert association.candidate_rider_track_id is None
    assert association.candidate_pillion_track_ids == ()
    assert set(association.unknown_track_ids) == set(association.person_track_ids)


def test_roles_remain_stable_across_consecutive_frames() -> None:
    processor = service()
    processor.process([vehicle(), person(125), person(220)], frame_id=1, timestamp=1.0)
    first = processor.process(
        [vehicle(110, frame_id=2), person(135, frame_id=2), person(230, frame_id=2)],
        frame_id=2,
        timestamp=2.0,
    ).associations[0]
    second = processor.process(
        [vehicle(120, frame_id=3), person(145, frame_id=3), person(240, frame_id=3)],
        frame_id=3,
        timestamp=3.0,
    ).associations[0]
    assert second.candidate_rider_track_id == first.candidate_rider_track_id
    assert second.candidate_pillion_track_ids == first.candidate_pillion_track_ids


def test_three_people_are_counted_only_for_their_vehicle() -> None:
    result = service().process(
        [vehicle(100), vehicle(500), person(120), person(185), person(250), person(540)]
    )
    counts = {item.vehicle_track_id: item.associated_person_count for item in result.associations}
    assert sorted(counts.values()) == [1, 3]
    assert sum(counts.values()) == 4


def test_three_people_distributed_across_vehicles_are_not_globally_grouped() -> None:
    result = service().process(
        [vehicle(100), vehicle(450), vehicle(800), person(130), person(480), person(830)]
    )
    assert [item.associated_person_count for item in result.associations] == [1, 1, 1]


def test_empty_detection_frame_preserves_tracking_result_shape() -> None:
    result = service().process(DetectionBatch([], InferenceMetrics("mock", "", "cpu", "loaded", 0.2)), frame_id=4)
    assert result.frame_id == 4
    assert result.vehicle_tracks == ()
    assert result.person_tracks == ()
    assert result.associations == ()


def test_malformed_detection_input_fails_explicitly() -> None:
    with pytest.raises(ValueError, match="DetectionResult"):
        service().process([None])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="positive area"):
        service().process([detection("person", (5, 5, 5, 20))])


def test_duplicate_detections_do_not_create_duplicate_tracks() -> None:
    result = service().process(
        [
            vehicle(),
            detection("motorcycle", (101, 101, 301, 251), confidence=0.8),
            person(),
            person(150, confidence=0.8),
        ]
    )
    assert len(result.vehicle_tracks) == 1
    assert len(result.person_tracks) == 1
    assert result.metrics.total_tracks_created == 2


def test_unconfigured_detector_classes_are_ignored() -> None:
    result = service().process(
        [vehicle(), person(), detection("helmet", (160, 10, 190, 35))]
    )
    assert len(result.vehicle_tracks) == 1
    assert len(result.person_tracks) == 1


def test_configured_class_names_are_used_without_inventing_detector_labels() -> None:
    processor = service(tracking_vehicle_classes="bike")
    result = processor.process(
        [detection("bike", (100, 100, 300, 250)), person()]
    )
    assert len(result.vehicle_tracks) == 1
    assert result.vehicle_tracks[0].class_name == "bike"
    assert len(result.person_tracks) == 1


def test_low_confidence_detections_are_not_tracked() -> None:
    result = service(track_min_confidence=0.8).process(
        [vehicle(confidence=0.79), person(confidence=0.79)]
    )
    assert result.vehicle_tracks == ()
    assert result.person_tracks == ()


def test_non_increasing_frame_ids_are_rejected() -> None:
    tracker = IoUObjectTracker()
    tracker.update([person(frame_id=2)], frame_id=2, timestamp=2.0)
    with pytest.raises(ValueError, match="frame_id must increase"):
        tracker.update([], frame_id=2, timestamp=3.0)
