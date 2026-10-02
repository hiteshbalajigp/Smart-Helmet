from pathlib import Path

from app.detection.yolo_loader import YOLODetector, YOLOModelStatus
from app.plate_detection.wpod_loader import WPODPlateDetector


def test_yolo_loader_reports_missing_weights(tmp_path: Path) -> None:
    missing_weights = tmp_path / "missing-yolo-weights.pt"
    result = YOLODetector(weights_path=missing_weights).load()

    assert result.loaded is False
    assert result.status == YOLOModelStatus.MODEL_NOT_AVAILABLE
    assert result.reason == "missing_model"
    assert result.model_path == missing_weights
    assert result.message == f"Model path missing: {missing_weights}"


def test_wpod_loader_reports_missing_weights() -> None:
    result = WPODPlateDetector().load()
    assert result.loaded is False
    assert "MODEL WEIGHT NOT YET INTEGRATED" in result.message
