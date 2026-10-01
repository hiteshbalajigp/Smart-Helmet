"""RAM-based circular buffer for pre/post violation evidence."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque

import cv2
import numpy as np

from utils.exceptions import EvidenceCaptureError
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BufferedFrame:
    frame: np.ndarray
    timestamp: float


class CircularEvidenceBuffer:
    """Store rolling window of frames in RAM."""

    def __init__(self, fps: int = 30, seconds_before: int = 10) -> None:
        self.fps = fps
        self.maxlen = fps * seconds_before
        self._buffer: Deque[BufferedFrame] = deque(maxlen=self.maxlen)
        self._lock = threading.Lock()

    def append(self, frame: np.ndarray) -> None:
        with self._lock:
            self._buffer.append(BufferedFrame(frame=frame.copy(), timestamp=time.time()))

    def get_before_frames(self) -> list[BufferedFrame]:
        with self._lock:
            return list(self._buffer)


class EvidenceCapture:
    """Capture evidence JPEG + MP4 on violation."""

    def __init__(
        self,
        output_dir: str = "evidence",
        fps: int = 30,
        seconds_before: int = 10,
        seconds_after: int = 10,
        jpeg_quality: int = 90,
        video_codec: str = "mp4v",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.fps = fps
        self.seconds_before = seconds_before
        self.seconds_after = seconds_after
        self.jpeg_quality = jpeg_quality
        self.video_codec = video_codec
        self.buffer = CircularEvidenceBuffer(fps, seconds_before)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def update(self, frame: np.ndarray) -> None:
        self.buffer.append(frame)

    def save_violation_evidence(
        self,
        violation_id: str,
        current_frame: np.ndarray,
        after_frames: list[np.ndarray] | None = None,
    ) -> dict[str, str]:
        """Save snapshot and video for a violation event."""
        try:
            event_dir = self.output_dir / violation_id
            event_dir.mkdir(parents=True, exist_ok=True)

            snapshot_path = event_dir / f"{violation_id}_snapshot.jpg"
            cv2.imwrite(
                str(snapshot_path),
                current_frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality],
            )

            before = [bf.frame for bf in self.buffer.get_before_frames()]
            after = after_frames or []
            all_frames = before + [current_frame] + after

            if not all_frames:
                raise EvidenceCaptureError("No frames available for evidence video")

            h, w = all_frames[0].shape[:2]
            video_path = event_dir / f"{violation_id}_evidence.mp4"
            writer = cv2.VideoWriter(
                str(video_path),
                cv2.VideoWriter_fourcc(*self.video_codec),
                self.fps,
                (w, h),
            )
            if not writer.isOpened():
                raise EvidenceCaptureError(f"Cannot open video writer: {video_path}")

            for frame in all_frames:
                writer.write(frame)
            writer.release()

            logger.info("Saved evidence for violation %s at %s", violation_id, event_dir)
            return {
                "snapshot": str(snapshot_path),
                "video": str(video_path),
                "directory": str(event_dir),
            }
        except EvidenceCaptureError:
            raise
        except Exception as exc:
            raise EvidenceCaptureError(f"Failed to save evidence: {exc}") from exc

    async def collect_after_frames(
        self,
        frame_source,
        count: int | None = None,
    ) -> list[np.ndarray]:
        """Collect post-violation frames from async/sync frame source."""
        target = count or self.fps * self.seconds_after
        frames: list[np.ndarray] = []
        for _ in range(target):
            frame = await frame_source() if hasattr(frame_source, "__await__") else frame_source()
            if frame is None:
                break
            frames.append(frame)
        return frames
