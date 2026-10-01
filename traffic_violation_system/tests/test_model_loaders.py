from app.detection.yolo_loader import YOLODetector
from app.plate_detection.wpod_loader import WPODPlateDetector


def test_yolo_loader_reports_missing_weights() -> None:
    result = YOLODetector().load()
    assert result.loaded is False
    assert "MODEL WEIGHT NOT YET INTEGRATED" in result.message


def test_wpod_loader_reports_missing_weights() -> None:
    result = WPODPlateDetector().load()
    assert result.loaded is False
    assert "MODEL WEIGHT NOT YET INTEGRATED" in result.message
