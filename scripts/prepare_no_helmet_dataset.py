"""Create starter YOLO label folders for no-helmet training."""

from __future__ import annotations

import argparse
from pathlib import Path

CLASS_NAMES = ["person", "motorcycle", "helmet", "no_helmet", "license_plate"]

LABELING_GUIDE = """
NO-HELMET LABELING GUIDE
========================

For each image, create a .txt file with the same name in datasets/processed/labels/

YOLO format: <class_id> <x_center> <y_center> <width> <height>  (normalized 0-1)

Class IDs:
  0 = person          -> full rider body on motorcycle
  1 = motorcycle      -> full bike/scooter
  2 = helmet          -> box around helmet on rider head
  3 = no_helmet       -> box around bare head (NO helmet visible)
  4 = license_plate   -> plate region

Rules for no_helmet detection:
  - Draw 'no_helmet' on every visible bare head
  - Draw 'helmet' when helmet is clearly visible
  - Always include 'person' + 'motorcycle' when both are visible
  - Use chin-mounted camera angle images for best results

Target: 5000+ no_helmet and 5000+ helmet examples each.
"""


def bootstrap_dataset(output_root: Path) -> None:
    for split in ("train", "val", "test"):
        (output_root / split / "images").mkdir(parents=True, exist_ok=True)
        (output_root / split / "labels").mkdir(parents=True, exist_ok=True)

    (output_root / "labels").mkdir(parents=True, exist_ok=True)
    (Path("datasets/raw/videos")).mkdir(parents=True, exist_ok=True)

    guide_path = output_root / "LABELING_GUIDE.txt"
    guide_path.write_text(LABELING_GUIDE.strip() + "\n", encoding="utf-8")
    print(guide_path.read_text(encoding="utf-8"))
    print(f"\nCreated dataset folders under: {output_root.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap no-helmet dataset folders")
    parser.add_argument("--output", default="datasets/processed")
    args = parser.parse_args()
    bootstrap_dataset(Path(args.output))


if __name__ == "__main__":
    main()
