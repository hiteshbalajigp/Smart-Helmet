#!/usr/bin/env python3
"""Classify images as helmet violation / no violation and push to dataset."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from inference.image_classifier import ClassificationResult, ImageViolationClassifier
from utils.config_loader import ConfigLoader
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

# Verified labels for seed images (manual review)
SEED_LABELS = {
    "traffic_multi_rider_no_helmet.jpg": "violation",
    "traffic_police_stop_no_helmet.jpg": "violation",
    "traffic_police_helmet_compliant.jpg": "no_violation",
    "traffic_highway_mixed_helmets.jpg": "violation",
    "traffic_dense_all_helmeted.jpg": "no_violation",
    "traffic_ola_both_helmeted.jpg": "no_violation",
    "traffic_triple_riding_no_helmet.jpg": "violation",
}


def import_seed_images(assets_dir: Path, inbox_dir: Path) -> list[Path]:
    """Copy user-provided seed images into incoming folder with clean names."""
    mapping = {
        "H1": "traffic_multi_rider_no_helmet.jpg",
        "H4": "traffic_police_stop_no_helmet.jpg",
        "H10": "traffic_police_helmet_compliant.jpg",
        "H7": "traffic_highway_mixed_helmets.jpg",
        "H8": "traffic_dense_all_helmeted.jpg",
        "H9": "traffic_ola_both_helmeted.jpg",
        "H5": "traffic_triple_riding_no_helmet.jpg",
    }

    inbox_dir.mkdir(parents=True, exist_ok=True)
    imported: list[Path] = []

    for src in sorted(assets_dir.glob("*.png")):
        key = next((k for k in mapping if f"images_{k}-" in src.name), None)
        name = mapping.get(key, f"incoming_{src.stem[:20]}.jpg") if key else f"incoming_{src.stem[:20]}.jpg"
        dest = inbox_dir / name
        shutil.copy2(src, dest)
        imported.append(dest)
        logger.info("Imported %s -> %s (%s)", src.name, dest.name, key or "unknown")

    return imported


def print_summary(results) -> None:
    print("\n" + "=" * 60)
    print("HELMET CLASSIFICATION SUMMARY")
    print("=" * 60)
    for item in results:
        status = item.result.value.upper()
        added = "YES" if item.added_to_dataset else "NO"
        print(f"\n{Path(item.image_path).name}")
        print(f"  Result:        {status}")
        print(f"  Violations:    {item.violation_count}")
        print(f"  no_helmet det: {item.no_helmet_count}")
        print(f"  helmet det:    {item.helmet_count}")
        print(f"  Added to dataset: {added}")
        if item.dataset_path:
            print(f"  Dataset path:  {item.dataset_path}")
    print("\n" + "=" * 60)

    violations = sum(1 for r in results if r.result == ClassificationResult.VIOLATION)
    compliant = sum(1 for r in results if r.result == ClassificationResult.NO_VIOLATION)
    print(f"Violations: {violations} | Compliant: {compliant} | Total: {len(results)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify images and collect violations into dataset")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--input", default="datasets/raw/incoming", help="Folder or image path")
    parser.add_argument("--import-seeds", action="store_true", help="Import provided seed images")
    parser.add_argument("--no-push", action="store_true", help="Classify only, do not copy to dataset")
    parser.add_argument("--manifest", default=None, help="JSON file with manual labels {filename: violation|no_violation}")
    parser.add_argument("--skip-model", action="store_true", help="Use manual labels only (faster, no YOLO inference)")
    args = parser.parse_args()

    config = ConfigLoader(args.config)
    setup_logging(config.get("logging.level", "INFO"), config.get("logging.file"))

    classifier = ImageViolationClassifier(config)
    input_path = Path(args.input)

    image_paths: list[Path] = []
    if args.import_seeds:
        candidates = [
            Path(__file__).resolve().parents[1].parent / "assets",
            Path(r"C:\Users\1185r\.cursor\projects\c-Users-1185r-Projects-smart-helmet-violation-detection\assets"),
            Path("assets"),
        ]
        assets = next((p for p in candidates if p.exists()), None)
        if assets is None:
            raise SystemExit("Assets folder not found. Place images in datasets/raw/incoming/")
        image_paths = import_seed_images(assets, input_path)
    elif input_path.is_file():
        image_paths = [input_path]
    else:
        image_paths = sorted(
            list(input_path.glob("*.jpg"))
            + list(input_path.glob("*.jpeg"))
            + list(input_path.glob("*.png"))
        )

    if not image_paths:
        raise SystemExit(f"No images found in {input_path}")

    manual_labels = dict(SEED_LABELS)
    if args.manifest:
        manual_labels.update(json.loads(Path(args.manifest).read_text(encoding="utf-8")))

    results = classifier.process_batch(
        image_paths,
        manual_labels=manual_labels,
        push=not args.no_push,
        skip_model=args.skip_model,
    )
    print_summary(results)


if __name__ == "__main__":
    main()
