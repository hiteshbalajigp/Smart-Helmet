from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np

from app.config.settings import Settings
from app.detection.detection_result import DetectionBox, DetectionResult
from app.detection.inference_service import YOLOv8InferenceService
from app.detection.yolo_loader import YOLODetector, YOLOModelStatus


class FakeYOLOModel:
    def __init__(self, weights_path: str) -> None:
        self.weights_path = weights_path

    def __call__(self, frame, **kwargs):
        return [
            types.SimpleNamespace(
                boxes=[
                    types.SimpleNamespace(
                        xyxy=[[10.0, 20.0, 100.0, 180.0]],
                        conf=[0.91],
                        cls=[2],
                    )
                ]
            )
        ]


def _install_fake_ultralytics(monkeypatch) -> None:
    fake_module = types.SimpleNamespace(YOLO=lambda path: FakeYOLOModel(path))
    monkeypatch.setitem(sys.modules, "ultralytics", fake_module)


def test_yolo_configuration_fields() -> None:
    settings = Settings()
    assert settings.yolo_model_path.name == "best.pt"
    assert settings.yolo_confidence_threshold > 0
    assert settings.yolo_iou_threshold > 0
    assert settings.yolo_image_size > 0
    assert settings.yolo_device in {"auto", "cpu", "cuda"}


def test_missing_model_is_reported_as_unavailable(tmp_path: Path) -> None:
    detector = YOLODetector(weights_path=tmp_path / "missing.pt")
    status = detector.status()
    assert status.loaded is False
    assert status.status == YOLOModelStatus.MODEL_NOT_AVAILABLE
    assert "missing.pt" in str(status.model_path)


def test_yolo_loader_can_load_with_mocked_framework(tmp_path: Path, monkeypatch) -> None:
    weights = tmp_path / "mock.pt"
    weights.write_text("fake weight")
    _install_fake_ultralytics(monkeypatch)

    detector = YOLODetector(weights_path=weights, device="cpu")
    result = detector.load()

    assert result.loaded is True
    assert result.status == YOLOModelStatus.MODEL_LOADED
    assert detector.is_loaded is True


def test_detection_result_creation_and_box_conversion() -> None:
    box = DetectionBox(x1=10, y1=20, x2=100, y2=180)
    detection = DetectionResult(
        class_id=0,
        class_name="person",
        confidence=0.89,
        bounding_box=box,
        frame_id=1,
        camera_id="cam-1",
    )

    assert detection.bounding_box.width == 90.0
    assert detection.bounding_box.height == 160.0
    assert detection.bounding_box.center_x == 55.0
    assert detection.bounding_box.center_y == 100.0
    assert detection.bounding_box.as_xyxy() == (10.0, 20.0, 100.0, 180.0)


def test_class_mapping_and_confidence_thresholding(tmp_path: Path, monkeypatch) -> None:
    weights = tmp_path / "mock.pt"
    weights.write_text("fake weight")
    _install_fake_ultralytics(monkeypatch)

    detector = YOLODetector(weights_path=weights, class_map={7: "rider"}, confidence_threshold=0.8)
    model_result = types.SimpleNamespace(
        boxes=[
            types.SimpleNamespace(
                xyxy=[[1.0, 2.0, 30.0, 40.0]],
                conf=[0.91],
                cls=[7],
            ),
            types.SimpleNamespace(
                xyxy=[[5.0, 10.0, 20.0, 25.0]],
                conf=[0.5],
                cls=[0],
            ),
        ]
    )

    detections = detector.parse_model_output(model_result)
    assert len(detections) == 1
    assert detections[0].class_name == "rider"
    assert detections[0].confidence == 0.91


def test_malformed_model_output_is_ignored(tmp_path: Path, monkeypatch) -> None:
    weights = tmp_path / "mock.pt"
    weights.write_text("fake weight")
    _install_fake_ultralytics(monkeypatch)

    detector = YOLODetector(weights_path=weights)
    malformed = types.SimpleNamespace(boxes=[types.SimpleNamespace(xyxy=None, conf=None, cls=None)])
    assert detector.parse_model_output(malformed) == []


def test_inference_service_uses_mocked_model(tmp_path: Path, monkeypatch) -> None:
    weights = tmp_path / "mock.pt"
    weights.write_text("fake weight")
    _install_fake_ultralytics(monkeypatch)

    detector = YOLODetector(weights_path=weights, device="cpu")
    service = YOLOv8InferenceService(detector=detector, camera_id="cam-1")
    batch = service.process_frame(np.zeros((64, 64, 3), dtype=np.uint8), camera_id="cam-1", frame_id=7, timestamp=123.0)

    assert len(batch.detections) == 1
    assert batch.detections[0].class_name == "helmet"
    assert batch.metrics.frame_count == 1
    assert batch.metrics.model_status == YOLOModelStatus.MODEL_LOADED.value


def test_inference_device_selection_and_cpu_fallback(monkeypatch) -> None:
    monkeypatch.setattr("app.detection.yolo_loader.YOLODetector._detect_runtime_device", lambda self: "cpu")
    detector = YOLODetector(weights_path=Path("mock.pt"), device="auto")
    assert detector._detect_runtime_device() == "cpu"
    assert detector.status().device == "cpu"


def test_inference_metrics_report_model_status(tmp_path: Path, monkeypatch) -> None:
    weights = tmp_path / "mock.pt"
    weights.write_text("fake weight")
    _install_fake_ultralytics(monkeypatch)

    detector = YOLODetector(weights_path=weights, device="cpu")
    service = YOLOv8InferenceService(detector=detector)
    batch = service.process_frame(np.zeros((32, 32, 3), dtype=np.uint8))

    assert batch.metrics.model_name == "mock.pt"
    assert batch.metrics.device == "cpu"
    assert batch.metrics.detection_count >= 0
