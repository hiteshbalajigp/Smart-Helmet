"""Performance metric collection scaffold."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    fps: float = 0.0
    frame_processing_ms: float = 0.0
    detection_ms: float = 0.0
    ocr_ms: float = 0.0
    database_ms: float = 0.0
    notification_ms: float = 0.0
    total_violation_processing_ms: float = 0.0


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._metrics = PerformanceMetrics()
        self._frame_timestamps: list[float] = []

    def record_frame(self) -> None:
        now = time.perf_counter()
        with self._lock:
            self._frame_timestamps.append(now)
            self._frame_timestamps = [ts for ts in self._frame_timestamps if (now - ts) <= 1.0]
            self._metrics.fps = float(len(self._frame_timestamps))

    def record_latency(self, field_name: str, elapsed_ms: float) -> None:
        with self._lock:
            if hasattr(self._metrics, field_name):
                setattr(self._metrics, field_name, elapsed_ms)

    def snapshot(self) -> PerformanceMetrics:
        with self._lock:
            return PerformanceMetrics(**self._metrics.__dict__)
