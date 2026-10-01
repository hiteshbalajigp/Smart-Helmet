"""Upload violation records from edge device to backend API."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx

from utils.config_loader import ConfigLoader
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def upload_report(api_url: str, report_path: Path) -> None:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    upload_payload = {
        "violation_id": payload["violation_id"],
        "violation_type": payload["violation_type"],
        "timestamp": payload["timestamp"],
        "track_id": payload["track_id"],
        "confidence": payload["confidence"],
        "plate_text": payload.get("plate_text"),
        "device_id": payload["metadata"]["device_id"],
        "gps": payload["metadata"].get("gps"),
        "metadata": payload["metadata"],
        "evidence": payload["evidence"],
    }
    response = httpx.post(f"{api_url.rstrip('/')}/violations", json=upload_payload, timeout=30)
    response.raise_for_status()
    logger.info("Uploaded violation %s", payload["violation_id"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync edge violation reports to API")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--report", required=True, help="Path to violation JSON report")
    args = parser.parse_args()

    config = ConfigLoader(args.config)
    setup_logging(config.get("logging.level", "INFO"))
    api_prefix = config.get("backend.api_prefix", "/api/v1")
    host = config.get("backend.host", "0.0.0.0")
    port = config.get("backend.port", 8000)
    api_url = f"http://{host}:{port}{api_prefix}"
    if host == "0.0.0.0":
        api_url = f"http://localhost:{port}{api_prefix}"

    upload_report(api_url, Path(args.report))


if __name__ == "__main__":
    main()
