from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FrameMetadata:
    frame_id: int
    timestamp: float
    camera_id: str
    width: int
    height: int
    fps: float


class LatestFrameProvider:
    """Simple bounded latest-frame provider for the detection pipeline."""

    def __init__(self, camera_id: str | None = None) -> None:
        self.camera_id = camera_id or "unknown"
        self._frame: Any | None = None
        self._metadata: FrameMetadata | None = None

    def update(self, frame: Any, metadata: FrameMetadata | None = None) -> None:
        self._frame = frame
        self._metadata = metadata or FrameMetadata(
            frame_id=0,
            timestamp=0.0,
            camera_id=self.camera_id,
            width=0,
            height=0,
            fps=0.0,
        )

    def get_latest(self) -> tuple[Any | None, FrameMetadata | None]:
        return self._frame, self._metadata

    @property
    def has_frame(self) -> bool:
        return self._frame is not None
