"""End-to-end real-time inference pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from inference.evidence_capture import EvidenceCapture
from inference.metadata import MetadataCollector
from inference.plate_ocr import PlateOCR
from inference.tracker import YOLOTracker
from inference.violation_detector import ViolationDetector, ViolationEvent
from inference.wpod_detector import WPODNetDetector
from utils.config_loader import ConfigLoader
from utils.geometry import clip_bbox
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


class InferencePipeline:
    """Real-time violation detection pipeline for edge deployment."""

    def __init__(self, config: ConfigLoader) -> None:
        inf_cfg = config.section("inference")
        viol_cfg = config.section("violations")
        plate_cfg = config.section("license_plate")
        ocr_cfg = config.section("ocr")
        ev_cfg = config.section("evidence")
        meta_cfg = config.section("metadata")

        model_path = inf_cfg.get("model_path")
        if not Path(model_path).exists():
            logger.warning("Model not found at %s; download/train weights first", model_path)

        self.tracker = YOLOTracker(
            model_path=model_path,
            confidence=inf_cfg["confidence"],
            iou=inf_cfg["iou"],
            tracker=inf_cfg["tracker"],
            device=inf_cfg["device"],
        )
        self.violation_detector = ViolationDetector(
            helmet_iou_threshold=viol_cfg["helmet_iou_threshold"],
            rider_motorcycle_iou=viol_cfg["rider_motorcycle_iou"],
            triple_riding_threshold=viol_cfg["triple_riding_threshold"],
            cooldown_sec=viol_cfg["cooldown_sec"],
            min_confidence=viol_cfg["min_confidence"],
            no_helmet_confidence=viol_cfg.get("no_helmet_confidence", 0.45),
            head_region_ratio=viol_cfg.get("head_region_ratio", 0.35),
            detect_standalone_no_helmet=viol_cfg.get("detect_standalone_no_helmet", True),
            require_motorcycle=viol_cfg.get("require_motorcycle", False),
            no_helmet_only=viol_cfg.get("no_helmet_only", False),
        )
        self.plate_detector = WPODNetDetector(
            model_path=plate_cfg["wpod_model_path"],
            min_width=plate_cfg["min_plate_width"],
            min_height=plate_cfg["min_plate_height"],
            skew_correction=plate_cfg["skew_correction"],
            perspective_correction=plate_cfg["perspective_correction"],
        )
        self.plate_ocr = PlateOCR(
            lang=ocr_cfg["lang"],
            use_angle_cls=ocr_cfg["use_angle_cls"],
            patterns=ocr_cfg["indian_plate_patterns"],
        )
        self.evidence = EvidenceCapture(
            output_dir=ev_cfg["output_dir"],
            fps=ev_cfg["fps"],
            seconds_before=ev_cfg["buffer_seconds_before"],
            seconds_after=ev_cfg["buffer_seconds_after"],
            jpeg_quality=ev_cfg["jpeg_quality"],
            video_codec=ev_cfg["video_codec"],
        )
        self.metadata = MetadataCollector(
            device_id=meta_cfg["device_id"],
            gps_enabled=meta_cfg["gps_enabled"],
            gps_port=meta_cfg["gps_port"],
            gps_baudrate=meta_cfg["gps_baudrate"],
        )
        self.reports_dir = Path("evidence/reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def process_frame(self, frame: np.ndarray) -> tuple[np.ndarray, list[dict[str, Any]]]:
        """Process single frame and return annotated frame + violation records."""
        self.evidence.update(frame)
        detections = self.tracker.track(frame)
        violations = self.violation_detector.process(detections)
        records: list[dict[str, Any]] = []

        for event in violations:
            record = self._handle_violation(frame, event, detections)
            if record:
                records.append(record)

        annotated = self._draw_annotations(frame, detections, violations)
        return annotated, records

    def _handle_violation(
        self,
        frame: np.ndarray,
        event: ViolationEvent,
        detections,
    ) -> dict[str, Any] | None:
        plate_text = self._extract_plate(frame, detections)
        meta = self.metadata.create_metadata(
            violation_id=event.violation_id,
            timestamp=event.timestamp,
        )
        evidence_paths = self.evidence.save_violation_evidence(event.violation_id, frame)

        record = {
            "violation_id": event.violation_id,
            "violation_type": event.violation_type.value,
            "timestamp": event.timestamp.isoformat(),
            "track_id": event.track_id,
            "confidence": event.confidence,
            "plate_text": plate_text,
            "metadata": meta.to_dict(),
            "evidence": evidence_paths,
        }
        self._save_report(record)
        logger.info("Violation detected: %s (%s)", event.violation_type.value, event.violation_id)
        return record

    def _extract_plate(self, frame: np.ndarray, detections) -> str | None:
        plates = [d for d in detections if d.class_name == "license_plate"]
        for plate_det in plates:
            bbox = clip_bbox(plate_det.bbox, frame.shape[1], frame.shape[0])
            x1, y1, x2, y2 = map(int, bbox.as_xyxy())
            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                continue
            wpod_results = self.plate_detector.detect(frame, roi)
            for result in wpod_results:
                ocr = self.plate_ocr.recognize(result.crop)
                if ocr.text:
                    return ocr.text
        wpod_results = self.plate_detector.detect(frame)
        for result in wpod_results:
            ocr = self.plate_ocr.recognize(result.crop)
            if ocr.text:
                return ocr.text
        return None

    def _save_report(self, record: dict[str, Any]) -> None:
        report_path = self.reports_dir / f"{record['violation_id']}.json"
        report_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    def _draw_annotations(self, frame, detections, violations) -> np.ndarray:
        output = frame.copy()
        color_map = {
            "person": (255, 200, 0),
            "motorcycle": (0, 165, 255),
            "helmet": (0, 255, 0),
            "no_helmet": (0, 0, 255),
            "license_plate": (255, 0, 255),
        }
        for det in detections:
            x1, y1, x2, y2 = map(int, det.bbox.as_xyxy())
            color = color_map.get(det.class_name, (200, 200, 200))
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
            label = f"{det.class_name} #{det.track_id}"
            cv2.putText(output, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        for event in violations:
            cv2.putText(
                output,
                f"VIOLATION: {event.violation_type.value.upper()}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 0, 255),
                3,
            )
        return output

    def run_video(self, source: str | int, display: bool = True, max_frames: int | None = None) -> None:
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video source: {source}")

        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            annotated, _ = self.process_frame(frame)
            if display:
                cv2.imshow("Smart Helmet Violation Detection", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            frame_count += 1
            if max_frames and frame_count >= max_frames:
                break

        cap.release()
        cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run violation detection inference")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--source", default="0", help="Video path or camera index")
    parser.add_argument("--no-display", action="store_true")
    parser.add_argument("--max-frames", type=int, default=None)
    args = parser.parse_args()

    config = ConfigLoader(args.config)
    setup_logging(config.get("logging.level", "INFO"), config.get("logging.file"))

    source: str | int = args.source
    if source.isdigit():
        source = int(source)

    pipeline = InferencePipeline(config)
    pipeline.run_video(source, display=not args.no_display, max_frames=args.max_frames)


if __name__ == "__main__":
    main()
