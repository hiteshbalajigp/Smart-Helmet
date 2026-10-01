#!/usr/bin/env python3
"""CLI entrypoints for common workflows."""

from __future__ import annotations

import argparse
import subprocess
import sys


def run_dataset_pipeline(config: str, no_augment: bool) -> int:
    cmd = [sys.executable, "-m", "training.dataset_pipeline", "--config", config]
    if no_augment:
        cmd.append("--no-augment")
    return subprocess.call(cmd)


def run_training(config: str, resume: bool) -> int:
    cmd = [sys.executable, "-m", "training.train_yolo", "--config", config]
    if resume:
        cmd.append("--resume")
    return subprocess.call(cmd)


def run_inference(config: str, source: str) -> int:
    cmd = [
        sys.executable,
        "-m",
        "inference.pipeline",
        "--config",
        config,
        "--source",
        source,
    ]
    return subprocess.call(cmd)


def run_edge_export(config: str, fmt: str) -> int:
    cmd = [
        sys.executable,
        "-m",
        "inference.edge_optimizer",
        "--config",
        config,
        "--format",
        fmt,
    ]
    return subprocess.call(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(description="Smart Helmet system scripts")
    sub = parser.add_subparsers(dest="command", required=True)

    ds = sub.add_parser("dataset", help="Run dataset pipeline")
    ds.add_argument("--config", default="configs/default.yaml")
    ds.add_argument("--no-augment", action="store_true")

    train = sub.add_parser("train", help="Train YOLOv8 model")
    train.add_argument("--config", default="configs/default.yaml")
    train.add_argument("--resume", action="store_true")

    infer = sub.add_parser("infer", help="Run inference pipeline")
    infer.add_argument("--config", default="configs/default.yaml")
    infer.add_argument("--source", default="0")

    edge = sub.add_parser("export", help="Export ONNX/TensorRT models")
    edge.add_argument("--config", default="configs/default.yaml")
    edge.add_argument("--format", default="all", choices=["onnx", "tensorrt", "all", "benchmark"])

    args = parser.parse_args()
    if args.command == "dataset":
        raise SystemExit(run_dataset_pipeline(args.config, args.no_augment))
    if args.command == "train":
        raise SystemExit(run_training(args.config, args.resume))
    if args.command == "infer":
        raise SystemExit(run_inference(args.config, args.source))
    if args.command == "export":
        raise SystemExit(run_edge_export(args.config, args.format))


if __name__ == "__main__":
    main()
