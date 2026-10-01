#!/usr/bin/env python3
"""Run no-helmet detection on camera or video."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from inference.pipeline import InferencePipeline
from utils.config_loader import ConfigLoader
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def ensure_model(config: ConfigLoader) -> Path:
    model_path = Path(config.get("inference.model_path"))
    if model_path.exists():
        return model_path

    logger.error("Trained model not found at: %s", model_path)
    print(
        "\nNo helmet detection model found. Train one first:\n"
        "  1. Put videos in datasets/raw/videos/\n"
        "  2. Label images with classes: person, motorcycle, helmet, no_helmet\n"
        "  3. Run: python scripts/run.py dataset\n"
        "  4. Run: python scripts/run.py train\n"
        "\nLabel the rider head as 'no_helmet' when no helmet is visible.\n"
        "Label as 'helmet' when a helmet is clearly worn.\n"
    )
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect riders without helmets")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--source", default="0", help="Camera index or video path")
    parser.add_argument("--no-display", action="store_true")
    args = parser.parse_args()

    config = ConfigLoader(args.config)
    setup_logging(config.get("logging.level", "INFO"), config.get("logging.file"))

    # Force no-helmet focused mode
    config.raw.setdefault("violations", {})["no_helmet_only"] = True

    ensure_model(config)

    source: str | int = args.source
    if str(source).isdigit():
        source = int(source)

    print("Starting no-helmet detection. Press 'q' in the video window to stop.")
    pipeline = InferencePipeline(config)
    pipeline.run_video(source, display=not args.no_display)


if __name__ == "__main__":
    main()
