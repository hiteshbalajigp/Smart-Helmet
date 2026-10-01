"""Dataset preparation pipeline for YOLO training."""

from __future__ import annotations

import argparse
import hashlib
import random
import shutil
from pathlib import Path
from typing import Iterable

import cv2
import imagehash
import numpy as np
import yaml
from PIL import Image

from training.augmentation import AugmentationPipeline
from utils.config_loader import ConfigLoader
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

CLASS_NAMES = ["person", "motorcycle", "helmet", "no_helmet", "license_plate"]


def extract_frames(
    video_path: Path,
    output_dir: Path,
    interval_sec: float = 0.5,
    max_frames: int = 1000,
) -> list[Path]:
    """Extract frames from video at fixed intervals."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_step = max(1, int(fps * interval_sec))
    saved: list[Path] = []
    frame_idx = 0
    saved_count = 0

    while saved_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_step == 0:
            out_path = output_dir / f"{video_path.stem}_{saved_count:06d}.jpg"
            cv2.imwrite(str(out_path), frame)
            saved.append(out_path)
            saved_count += 1
        frame_idx += 1

    cap.release()
    logger.info("Extracted %d frames from %s", len(saved), video_path.name)
    return saved


def compute_phash(image_path: Path) -> imagehash.ImageHash:
    with Image.open(image_path) as img:
        return imagehash.phash(img)


def remove_duplicate_frames(
    image_dir: Path,
    threshold: int = 5,
) -> tuple[list[Path], int]:
    """Remove near-duplicate frames using perceptual hashing."""
    images = sorted(image_dir.glob("*.jpg")) + sorted(image_dir.glob("*.png"))
    unique: list[Path] = []
    hashes: list[imagehash.ImageHash] = []
    removed = 0

    for img_path in images:
        current_hash = compute_phash(img_path)
        is_duplicate = any(current_hash - prev <= threshold for prev in hashes)
        if is_duplicate:
            img_path.unlink(missing_ok=True)
            removed += 1
            continue
        hashes.append(current_hash)
        unique.append(img_path)

    logger.info("Removed %d duplicate frames from %s", removed, image_dir)
    return unique, removed


def split_dataset(
    image_paths: Iterable[Path],
    labels_dir: Path,
    output_root: Path,
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    seed: int = 42,
) -> dict[str, list[Path]]:
    """Split images and labels into train/val/test."""
    images = list(image_paths)
    random.Random(seed).shuffle(images)
    n = len(images)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)

    splits = {
        "train": images[:train_end],
        "val": images[train_end:val_end],
        "test": images[val_end:],
    }

    for split_name, split_images in splits.items():
        img_out = output_root / split_name / "images"
        lbl_out = output_root / split_name / "labels"
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        for img_path in split_images:
            dest_img = img_out / img_path.name
            shutil.copy2(img_path, dest_img)
            label_src = labels_dir / f"{img_path.stem}.txt"
            if label_src.exists():
                shutil.copy2(label_src, lbl_out / label_src.name)

    logger.info(
        "Split dataset: train=%d val=%d test=%d",
        len(splits["train"]),
        len(splits["val"]),
        len(splits["test"]),
    )
    return splits


def write_data_yaml(output_root: Path, config_path: Path) -> Path:
    """Generate YOLO data.yaml."""
    data = {
        "path": str(output_root.resolve()),
        "train": "train/images",
        "val": "val/images",
        "test": "test/images",
        "names": {idx: name for idx, name in enumerate(CLASS_NAMES)},
        "nc": len(CLASS_NAMES),
    }
    yaml_path = config_path / "data.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    with yaml_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False)
    return yaml_path


def augment_split(
    split_dir: Path,
    aug_pipeline: AugmentationPipeline,
    multiplier: int = 2,
) -> int:
    """Apply augmentation to labeled images in a split."""
    images_dir = split_dir / "images"
    labels_dir = split_dir / "labels"
    generated = 0

    for img_path in sorted(images_dir.glob("*.jpg")):
        label_path = labels_dir / f"{img_path.stem}.txt"
        if not label_path.exists():
            continue
        image = cv2.imread(str(img_path))
        if image is None:
            continue
        bboxes, class_ids = _load_yolo_labels(label_path, image.shape[1], image.shape[0])

        for aug_idx in range(multiplier):
            aug_image, aug_bboxes, aug_classes = aug_pipeline(image, bboxes, class_ids)
            out_name = f"{img_path.stem}_aug{aug_idx}"
            out_img = images_dir / f"{out_name}.jpg"
            out_lbl = labels_dir / f"{out_name}.txt"
            cv2.imwrite(str(out_img), aug_image)
            _save_yolo_labels(out_lbl, aug_bboxes, aug_classes, aug_image.shape[1], aug_image.shape[0])
            generated += 1

    logger.info("Generated %d augmented images in %s", generated, split_dir)
    return generated


def _load_yolo_labels(
    label_path: Path,
    img_w: int,
    img_h: int,
) -> tuple[list[list[float]], list[int]]:
    bboxes: list[list[float]] = []
    class_ids: list[int] = []
    with label_path.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 5:
                continue
            cls_id = int(parts[0])
            cx, cy, w, h = map(float, parts[1:])
            x1 = (cx - w / 2) * img_w
            y1 = (cy - h / 2) * img_h
            x2 = (cx + w / 2) * img_w
            y2 = (cy + h / 2) * img_h
            bboxes.append([x1, y1, x2, y2])
            class_ids.append(cls_id)
    return bboxes, class_ids


def _save_yolo_labels(
    label_path: Path,
    bboxes: list[list[float]],
    class_ids: list[int],
    img_w: int,
    img_h: int,
) -> None:
    lines: list[str] = []
    for bbox, cls_id in zip(bboxes, class_ids):
        x1, y1, x2, y2 = bbox
        cx = ((x1 + x2) / 2) / img_w
        cy = ((y1 + y2) / 2) / img_h
        w = (x2 - x1) / img_w
        h = (y2 - y1) / img_h
        lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    label_path.write_text("\n".join(lines), encoding="utf-8")


def run_pipeline(config: ConfigLoader, augment: bool = True) -> None:
    """Execute full dataset pipeline."""
    ds_cfg = config.section("dataset")
    raw_videos = Path(ds_cfg["raw_videos"])
    processed = Path(ds_cfg["root"])
    frames_dir = processed / "frames"
    labels_dir = processed / "labels"
    frames_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    all_frames: list[Path] = []
    for video in sorted(raw_videos.glob("**/*")):
        if video.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"}:
            all_frames.extend(
                extract_frames(
                    video,
                    frames_dir,
                    interval_sec=ds_cfg["frame_extraction"]["interval_sec"],
                    max_frames=ds_cfg["frame_extraction"]["max_frames_per_video"],
                )
            )

    unique_frames, _ = remove_duplicate_frames(frames_dir, ds_cfg["dedup"]["hash_threshold"])
    splits = split_dataset(
        unique_frames,
        labels_dir,
        processed,
        train_ratio=ds_cfg["split_ratios"]["train"],
        val_ratio=ds_cfg["split_ratios"]["val"],
    )

    if augment:
        aug = AugmentationPipeline(config.section("augmentation"))
        for split in ("train", "val"):
            augment_split(processed / split, aug, multiplier=2)

    write_data_yaml(processed, Path("configs"))
    logger.info("Dataset pipeline complete. Splits: %s", {k: len(v) for k, v in splits.items()})


def main() -> None:
    parser = argparse.ArgumentParser(description="Dataset preparation pipeline")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--no-augment", action="store_true")
    args = parser.parse_args()

    config = ConfigLoader(args.config)
    setup_logging(config.get("logging.level", "INFO"), config.get("logging.file"))
    run_pipeline(config, augment=not args.no_augment)


if __name__ == "__main__":
    main()
