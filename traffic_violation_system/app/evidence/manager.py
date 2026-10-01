"""Evidence file management (original + annotated)."""

from __future__ import annotations

import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np

from app.config.settings import get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class EvidenceManager:
    def __init__(self) -> None:
        settings = get_settings()
        self.original_dir = settings.evidence_dir
        self.annotated_dir = settings.annotated_evidence_dir

    def _build_paths(self, camera_id: str, event_id: str) -> tuple[Path, Path]:
        date_part = datetime.utcnow().strftime("%Y%m%d")
        base_name = f"{camera_id}_{event_id}_{uuid4().hex[:8]}"
        original = self.original_dir / date_part / f"{base_name}.jpg"
        annotated = self.annotated_dir / date_part / f"{base_name}_annotated.jpg"
        original.parent.mkdir(parents=True, exist_ok=True)
        annotated.parent.mkdir(parents=True, exist_ok=True)
        return original, annotated

    @staticmethod
    def _checksum(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def save_from_array(
        self,
        camera_id: str,
        event_id: str,
        frame: np.ndarray,
        annotated_frame: np.ndarray | None = None,
    ) -> tuple[str, str | None, str | None]:
        original_path, annotated_path = self._build_paths(camera_id, event_id)
        if not cv2.imwrite(str(original_path), frame):
            raise RuntimeError(f"Failed to write original evidence: {original_path}")

        annotated_written: str | None = None
        if annotated_frame is not None:
            if not cv2.imwrite(str(annotated_path), annotated_frame):
                logger.warning("Failed to write annotated evidence for event %s", event_id)
            else:
                annotated_written = str(annotated_path)

        checksum = self._checksum(original_path)
        return str(original_path), annotated_written, checksum

    def copy_existing_file(self, source: Path, camera_id: str, event_id: str) -> str:
        original_path, _ = self._build_paths(camera_id, event_id)
        shutil.copy2(source, original_path)
        return str(original_path)
