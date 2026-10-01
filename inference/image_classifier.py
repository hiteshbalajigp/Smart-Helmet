"""Classify images for helmet violations and collect into training dataset."""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from inference.tracker import CLASS_ID_TO_NAME, TrackedDetection, YOLOTracker
from inference.violation_detector import ViolationDetector, ViolationType
from utils.config_loader import ConfigLoader
from utils.geometry import BoundingBox
from utils.logger import get_logger

logger = get_logger(__name__)

CLASS_NAME_TO_ID = {v: k for k, v in CLASS_ID_TO_NAME.items()}


class ClassificationResult(str, Enum):
    VIOLATION = "violation"
    NO_VIOLATION = "no_violation"
    UNCERTAIN = "uncertain"


@dataclass
class ImageClassification:
    image_path: str
    result: ClassificationResult
    violation_count: int
    helmet_count: int
    no_helmet_count: int
    person_count: int
    motorcycle_count: int
    violations: list[dict[str, Any]] = field(default_factory=list)
    detections: list[dict[str, Any]] = field(default_factory=list)
    added_to_dataset: bool = False
    dataset_path: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ImageViolationClassifier:
    """Classify static images and push violations into YOLO dataset folders."""

    def __init__(self, config: ConfigLoader) -> None:
        inf_cfg = config.section("inference")
        viol_cfg = config.section("violations")
        ds_cfg = config.section("dataset")

        model_path = inf_cfg["model_path"]
        self.use_custom_model = Path(model_path).exists()
        self.model_path = model_path if self.use_custom_model else "yolov8m.pt"

        self.tracker = YOLOTracker(
            model_path=self.model_path,
            confidence=inf_cfg["confidence"],
            iou=inf_cfg["iou"],
            device="cpu" if inf_cfg.get("device", "auto") == "auto" else inf_cfg["device"],
        )
        self.violation_detector = ViolationDetector(
            helmet_iou_threshold=viol_cfg.get("helmet_iou_threshold", 0.25),
            rider_motorcycle_iou=viol_cfg.get("rider_motorcycle_iou", 0.15),
            triple_riding_threshold=viol_cfg.get("triple_riding_threshold", 2),
            cooldown_sec=0.0,
            min_confidence=viol_cfg.get("min_confidence", 0.45),
            no_helmet_confidence=viol_cfg.get("no_helmet_confidence", 0.40),
            head_region_ratio=viol_cfg.get("head_region_ratio", 0.35),
            detect_standalone_no_helmet=viol_cfg.get("detect_standalone_no_helmet", True),
            require_motorcycle=viol_cfg.get("require_motorcycle", False),
            no_helmet_only=viol_cfg.get("no_helmet_only", True),
        )

        self.dataset_root = Path(ds_cfg.get("root", "datasets/processed"))
        self.violation_dir = self.dataset_root / "train" / "images"
        self.compliant_dir = self.dataset_root / "val" / "images"
        self.violation_labels = self.dataset_root / "train" / "labels"
        self.compliant_labels = self.dataset_root / "val" / "labels"
        self.inbox_dir = Path("datasets/raw/incoming")
        self.reports_dir = Path("datasets/reports")

        for path in (
            self.violation_dir,
            self.compliant_dir,
            self.violation_labels,
            self.compliant_labels,
            self.inbox_dir,
            self.reports_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def classify_image(self, image_path: Path) -> ImageClassification:
        frame = cv2.imread(str(image_path))
        if frame is None:
            raise ValueError(f"Cannot read image: {image_path}")

        detections = self.tracker.track(frame)
        events = self.violation_detector.process(detections)

        helmet_count = sum(1 for d in detections if d.class_name == "helmet")
        no_helmet_count = sum(1 for d in detections if d.class_name == "no_helmet")
        person_count = sum(1 for d in detections if d.class_name == "person")
        motorcycle_count = sum(1 for d in detections if d.class_name == "motorcycle")

        if events or no_helmet_count > 0:
            result = ClassificationResult.VIOLATION
        elif helmet_count > 0 and no_helmet_count == 0:
            result = ClassificationResult.NO_VIOLATION
        elif not self.use_custom_model:
            result = self._fallback_classify(detections)
        else:
            result = ClassificationResult.UNCERTAIN

        return ImageClassification(
            image_path=str(image_path),
            result=result,
            violation_count=len(events),
            helmet_count=helmet_count,
            no_helmet_count=no_helmet_count,
            person_count=person_count,
            motorcycle_count=motorcycle_count,
            violations=[
                {
                    "violation_type": e.violation_type.value,
                    "track_id": e.track_id,
                    "confidence": e.confidence,
                }
                for e in events
            ],
            detections=[
                {
                    "class": d.class_name,
                    "confidence": d.bbox.confidence,
                    "bbox": d.bbox.as_xyxy(),
                }
                for d in detections
            ],
        )

    def _fallback_classify(self, detections: list[TrackedDetection]) -> ClassificationResult:
        """
        Bootstrap mode when custom helmet model is not trained yet.
        Uses COCO person+motorcycle presence and defers to manual review manifest.
        """
        persons = [d for d in detections if d.class_name == "person"]
        motorcycles = [d for d in detections if d.class_name == "motorcycle"]
        if persons and motorcycles:
            return ClassificationResult.UNCERTAIN
        if persons or motorcycles:
            return ClassificationResult.UNCERTAIN
        return ClassificationResult.UNCERTAIN

    def push_to_dataset(
        self,
        classification: ImageClassification,
        source_path: Path,
        force_split: str | None = None,
    ) -> ImageClassification:
        """Copy classified image and auto-labels into train (violation) or val (compliant)."""
        if classification.result == ClassificationResult.UNCERTAIN:
            return classification

        split = force_split or (
            "train" if classification.result == ClassificationResult.VIOLATION else "val"
        )
        img_dir = self.dataset_root / split / "images"
        lbl_dir = self.dataset_root / split / "labels"
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        stem = f"{source_path.stem}_{uuid.uuid4().hex[:8]}"
        dest_img = img_dir / f"{stem}{source_path.suffix.lower()}"
        dest_lbl = lbl_dir / f"{stem}.txt"

        shutil.copy2(source_path, dest_img)
        self._write_yolo_labels(dest_lbl, classification, cv2.imread(str(source_path)))

        classification.added_to_dataset = True
        classification.dataset_path = str(dest_img)
        logger.info("Added %s image to dataset: %s", classification.result.value, dest_img)
        return classification

    def _write_yolo_labels(
        self,
        label_path: Path,
        classification: ImageClassification,
        frame: np.ndarray | None,
    ) -> None:
        if frame is None:
            label_path.write_text("", encoding="utf-8")
            return

        h, w = frame.shape[:2]
        lines: list[str] = []

        for det in classification.detections:
            cls_name = det["class"]
            if cls_name not in CLASS_NAME_TO_ID:
                continue
            x1, y1, x2, y2 = det["bbox"]
            cx = ((x1 + x2) / 2) / w
            cy = ((y1 + y2) / 2) / h
            bw = (x2 - x1) / w
            bh = (y2 - y1) / h
            lines.append(
                f"{CLASS_NAME_TO_ID[cls_name]} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"
            )

        if classification.result == ClassificationResult.VIOLATION and not any(
            line.startswith("3 ") for line in lines
        ):
            for det in classification.detections:
                if det["class"] != "person":
                    continue
                x1, y1, x2, y2 = det["bbox"]
                head_h = (y2 - y1) * 0.35
                hx1, hy1, hx2, hy2 = x1, y1, x2, y1 + head_h
                cx = ((hx1 + hx2) / 2) / w
                cy = ((hy1 + hy2) / 2) / h
                bw = (hx2 - hx1) / w
                bh = (hy2 - hy1) / h
                lines.append(f"3 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

        label_path.write_text("\n".join(lines), encoding="utf-8")

    def process_batch(
        self,
        image_paths: list[Path],
        manual_labels: dict[str, str] | None = None,
        push: bool = True,
        skip_model: bool = False,
    ) -> list[ImageClassification]:
        manual_labels = manual_labels or {}
        results: list[ImageClassification] = []

        for path in image_paths:
            manual = manual_labels.get(path.name) or manual_labels.get(str(path))
            if skip_model and manual:
                classification = ImageClassification(
                    image_path=str(path),
                    result=ClassificationResult(manual),
                    violation_count=1 if manual == "violation" else 0,
                    helmet_count=0 if manual == "violation" else 1,
                    no_helmet_count=1 if manual == "violation" else 0,
                    person_count=0,
                    motorcycle_count=0,
                    violations=[{"source": "manual_review", "label": manual}],
                )
            else:
                classification = self.classify_image(path)
                if manual:
                    classification.result = ClassificationResult(manual)
                    classification.violations = [{"source": "manual_review", "label": manual}]

            if push and classification.result != ClassificationResult.UNCERTAIN:
                classification = self.push_to_dataset(classification, path)

            results.append(classification)

        report_path = self.reports_dir / f"classification_{datetime.now():%Y%m%d_%H%M%S}.json"
        report_path.write_text(
            json.dumps([asdict(r) for r in results], indent=2),
            encoding="utf-8",
        )
        logger.info("Saved classification report: %s", report_path)
        return results
