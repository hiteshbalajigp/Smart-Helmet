"""PyTorch -> ONNX -> TensorRT optimization pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ultralytics import YOLO

from utils.config_loader import ConfigLoader
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def export_onnx(config: ConfigLoader) -> Path:
    inf_cfg = config.section("inference")
    edge_cfg = config.section("edge")
    model_path = inf_cfg["model_path"]
    onnx_path = Path(inf_cfg["onnx_path"])
    onnx_path.parent.mkdir(parents=True, exist_ok=True)

    model = YOLO(model_path)
    model.export(
        format="onnx",
        imgsz=inf_cfg.get("imgsz", 640),
        opset=edge_cfg["onnx_opset"],
        simplify=True,
        dynamic=False,
    )

    exported = Path(model_path).with_suffix(".onnx")
    if exported.exists() and exported != onnx_path:
        onnx_path.write_bytes(exported.read_bytes())
        exported.unlink(missing_ok=True)

    logger.info("Exported ONNX model to %s", onnx_path)
    return onnx_path


def export_tensorrt(config: ConfigLoader) -> Path:
    inf_cfg = config.section("inference")
    edge_cfg = config.section("edge")
    engine_path = Path(inf_cfg["tensorrt_path"])
    engine_path.parent.mkdir(parents=True, exist_ok=True)

    onnx_path = Path(inf_cfg["onnx_path"])
    if not onnx_path.exists():
        export_onnx(config)

    model = YOLO(str(onnx_path))
    model.export(
        format="engine",
        imgsz=inf_cfg.get("imgsz", 640),
        half=edge_cfg["tensorrt_fp16"],
        int8=edge_cfg["tensorrt_int8"],
        batch=edge_cfg["max_batch_size"],
        workspace=edge_cfg["workspace_size_mb"],
        device=0,
    )

    exported = onnx_path.with_suffix(".engine")
    if exported.exists() and exported != engine_path:
        engine_path.write_bytes(exported.read_bytes())

    logger.info("Exported TensorRT engine to %s", engine_path)
    return engine_path


def benchmark_model(config: ConfigLoader, model_path: str, runs: int = 100) -> dict:
    import time

    import numpy as np

    model = YOLO(model_path)
    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    latencies: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        model.predict(dummy, verbose=False)
        latencies.append((time.perf_counter() - start) * 1000)

    stats = {
        "model": model_path,
        "runs": runs,
        "mean_ms": sum(latencies) / len(latencies),
        "min_ms": min(latencies),
        "max_ms": max(latencies),
        "fps": 1000.0 / (sum(latencies) / len(latencies)),
    }
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Edge model optimization")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--format", choices=["onnx", "tensorrt", "all", "benchmark"], default="all")
    args = parser.parse_args()

    config = ConfigLoader(args.config)
    setup_logging(config.get("logging.level", "INFO"), config.get("logging.file"))

    results = {}
    if args.format in {"onnx", "all"}:
        results["onnx"] = str(export_onnx(config))
    if args.format in {"tensorrt", "all"}:
        results["tensorrt"] = str(export_tensorrt(config))
    if args.format == "benchmark":
        inf_cfg = config.section("inference")
        for path_key in ("model_path", "onnx_path", "tensorrt_path"):
            path = inf_cfg[path_key]
            if Path(path).exists():
                results[path_key] = benchmark_model(config, path)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
