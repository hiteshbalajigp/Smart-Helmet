"""Unit tests for violation rules."""

from inference.tracker import TrackedDetection
from inference.violation_detector import ViolationDetector, ViolationType
from utils.geometry import BoundingBox


def _det(class_name: str, box: BoundingBox, track_id: int) -> TrackedDetection:
    class_map = {
        "person": 0,
        "motorcycle": 1,
        "helmet": 2,
        "no_helmet": 3,
        "license_plate": 4,
    }
    box = BoundingBox(
        box.x1,
        box.y1,
        box.x2,
        box.y2,
        confidence=box.confidence,
        class_id=class_map[class_name],
        track_id=track_id,
    )
    return TrackedDetection(bbox=box, class_name=class_name, track_id=track_id)


def test_triple_riding_violation():
    detector = ViolationDetector(triple_riding_threshold=2, cooldown_sec=0, rider_motorcycle_iou=0.1)
    moto = _det("motorcycle", BoundingBox(0, 0, 200, 200, confidence=0.9), 1)
    riders = [
        _det("person", BoundingBox(20, 20, 80, 180, confidence=0.9), 2),
        _det("person", BoundingBox(60, 20, 120, 180, confidence=0.9), 3),
        _det("person", BoundingBox(100, 20, 160, 180, confidence=0.9), 4),
    ]
    events = detector.process([moto, *riders])
    assert any(e.violation_type == ViolationType.TRIPLE_RIDING for e in events)


def test_no_helmet_violation():
    detector = ViolationDetector(cooldown_sec=0, rider_motorcycle_iou=0.1)
    moto = _det("motorcycle", BoundingBox(0, 0, 200, 200, confidence=0.9), 1)
    rider = _det("person", BoundingBox(20, 20, 80, 180, confidence=0.9), 2)
    no_helmet = _det("no_helmet", BoundingBox(30, 30, 70, 80, confidence=0.9), 3)
    events = detector.process([moto, rider, no_helmet])
    assert any(e.violation_type == ViolationType.NO_HELMET for e in events)


def test_direct_no_helmet_without_motorcycle():
    detector = ViolationDetector(
        cooldown_sec=0,
        detect_standalone_no_helmet=True,
        require_motorcycle=False,
        no_helmet_only=True,
    )
    no_helmet = _det("no_helmet", BoundingBox(50, 50, 120, 130, confidence=0.92), 10)
    events = detector.process([no_helmet])
    assert any(e.violation_type == ViolationType.NO_HELMET for e in events)


def test_no_helmet_only_skips_triple_riding():
    detector = ViolationDetector(
        triple_riding_threshold=2,
        cooldown_sec=0,
        rider_motorcycle_iou=0.1,
        no_helmet_only=True,
    )
    moto = _det("motorcycle", BoundingBox(0, 0, 200, 200, confidence=0.9), 1)
    riders = [
        _det("person", BoundingBox(20, 20, 80, 180, confidence=0.9), 2),
        _det("person", BoundingBox(60, 20, 120, 180, confidence=0.9), 3),
        _det("person", BoundingBox(100, 20, 160, 180, confidence=0.9), 4),
    ]
    events = detector.process([moto, *riders])
    assert not any(e.violation_type == ViolationType.TRIPLE_RIDING for e in events)
