"""YOLOv8 training with transfer learning and evaluation metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import seaborn as sns
import yaml
from ultralytics import YOLO

from utils.config_loader import ConfigLoader
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def train_yolov8(config: ConfigLoader, resume: bool = False) -> dict[str, Any]:
    """Train YOLOv8m with configured hyperparameters."""
    train_cfg = config.section("training")
    data_yaml = Path("configs/data.yaml")
    if not data_yaml.exists():
        raise FileNotFoundError(
            "configs/data.yaml not found. Run dataset pipeline first or create manually."
        )

    model_name = train_cfg["model"]
    if resume:
        weights = Path(train_cfg["project"]) / train_cfg["name"] / "weights" / "last.pt"
        model = YOLO(str(weights))
        logger.info("Resuming training from %s", weights)
    else:
        model = YOLO(model_name)
        logger.info("Starting transfer learning from %s", model_name)

    results = model.train(
        data=str(data_yaml),
        epochs=train_cfg["epochs"],
        patience=train_cfg["patience"],
        batch=train_cfg["batch_size"],
        imgsz=train_cfg["imgsz"],
        optimizer=train_cfg["optimizer"],
        lr0=train_cfg["lr0"],
        lrf=train_cfg["lrf"],
        weight_decay=train_cfg["weight_decay"],
        warmup_epochs=train_cfg["warmup_epochs"],
        cos_lr=train_cfg["cos_lr"],
        amp=train_cfg["amp"],
        workers=train_cfg["workers"],
        seed=train_cfg["seed"],
        project=train_cfg["project"],
        name=train_cfg["name"],
        save=True,
        save_period=train_cfg["save_period"],
        resume=resume,
        plots=True,
        val=True,
        exist_ok=True,
    )

    metrics = evaluate_model(model, data_yaml, train_cfg)
    save_training_report(metrics, Path(train_cfg["project"]) / train_cfg["name"])
    return metrics


def evaluate_model(model: YOLO, data_yaml: Path, train_cfg: dict[str, Any]) -> dict[str, Any]:
    """Run validation and export metrics."""
    val_results = model.val(data=str(data_yaml), split="val", plots=True)
    metrics = {
        "precision": float(getattr(val_results.box, "mp", 0.0)),
        "recall": float(getattr(val_results.box, "mr", 0.0)),
        "map50": float(getattr(val_results.box, "map50", 0.0)),
        "map50_95": float(getattr(val_results.box, "map", 0.0)),
    }

    run_dir = Path(train_cfg["project"]) / train_cfg["name"]
    _plot_confusion_matrix(run_dir)
    metrics_path = run_dir / "metrics_summary.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    logger.info("Validation metrics: %s", metrics)
    return metrics


def _plot_confusion_matrix(run_dir: Path) -> None:
    """Generate confusion matrix plot if Ultralytics outputs exist."""
    cm_npy = run_dir / "confusion_matrix.npy"
    if not cm_npy.exists():
        return
    import numpy as np

    matrix = np.load(cm_npy)
    plt.figure(figsize=(8, 6))
    sns.heatmap(matrix, annot=True, fmt=".2f", cmap="Blues")
    plt.title("Confusion Matrix")
    plt.tight_layout()
    plt.savefig(run_dir / "confusion_matrix_custom.png")
    plt.close()


def export_best_weights(config: ConfigLoader) -> Path:
    """Copy best.pt to models/checkpoints for inference."""
    train_cfg = config.section("training")
    src = Path(train_cfg["project"]) / train_cfg["name"] / "weights" / "best.pt"
    dst_dir = Path("models/checkpoints")
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "best.pt"
    if src.exists():
        dst.write_bytes(src.read_bytes())
        logger.info("Exported best weights to %s", dst)
    return dst


def main() -> None:
    parser = argparse.ArgumentParser(description="Train YOLOv8 violation detector")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    config = ConfigLoader(args.config)
    setup_logging(config.get("logging.level", "INFO"), config.get("logging.file"))
    metrics = train_yolov8(config, resume=args.resume)
    export_best_weights(config)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
