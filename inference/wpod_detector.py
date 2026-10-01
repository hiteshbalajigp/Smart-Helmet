"""WPOD-NET license plate detection with perspective correction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from utils.exceptions import ModelLoadError
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PlateDetection:
    crop: np.ndarray
    corners: np.ndarray
    confidence: float


class WPODNetDetector:
    """
    WPOD-NET wrapper for license plate localization.

    Expects a pre-trained WPOD-NET H5 model at configured path.
    Falls back to contour-based detection when model is unavailable.
    """

    def __init__(
        self,
        model_path: str,
        min_width: int = 80,
        min_height: int = 20,
        skew_correction: bool = True,
        perspective_correction: bool = True,
    ) -> None:
        self.model_path = Path(model_path)
        self.min_width = min_width
        self.min_height = min_height
        self.skew_correction = skew_correction
        self.perspective_correction = perspective_correction
        self._model: Any = None
        self._load_model()

    def _load_model(self) -> None:
        if not self.model_path.exists():
            logger.warning("WPOD model not found at %s; using fallback detector", self.model_path)
            return
        try:
            import tensorflow as tf

            self._model = tf.keras.models.load_model(str(self.model_path), compile=False)
            logger.info("Loaded WPOD-NET model from %s", self.model_path)
        except Exception as exc:
            logger.warning("Failed to load WPOD model: %s", exc)
            self._model = None

    def detect(self, image: np.ndarray, roi: np.ndarray | None = None) -> list[PlateDetection]:
        target = roi if roi is not None else image
        if self._model is not None:
            try:
                return self._detect_wpod(target)
            except Exception as exc:
                logger.error("WPOD inference failed: %s", exc)
        return self._detect_fallback(target)

    def _detect_wpod(self, image: np.ndarray) -> list[PlateDetection]:
        import tensorflow as tf

        input_img = cv2.resize(image, (208, 208)).astype(np.float32) / 255.0
        input_batch = np.expand_dims(input_img, axis=0)
        outputs = self._model.predict(input_batch, verbose=0)
        detections: list[PlateDetection] = []

        # Generic WPOD output parsing (model-specific tuning may be required)
        if isinstance(outputs, list) and len(outputs) >= 2:
            probs = outputs[0][0]
            affines = outputs[1][0]
            for idx, prob in enumerate(probs):
                if prob < 0.5:
                    continue
                affine = affines[idx].reshape(2, 3)
                h, w = image.shape[:2]
                corners = self._affine_to_corners(affine, w, h)
                crop = self._warp_plate(image, corners)
                if crop.size > 0:
                    detections.append(PlateDetection(crop=crop, corners=corners, confidence=float(prob)))
        return detections

    def _detect_fallback(self, image: np.ndarray) -> list[PlateDetection]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        edges = cv2.Canny(gray, 30, 200)
        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

        detections: list[PlateDetection] = []
        for contour in contours:
            rect = cv2.minAreaRect(contour)
            (cx, cy), (w, h), angle = rect
            if w < h:
                w, h = h, w
            if w < self.min_width or h < self.min_height:
                continue
            box = cv2.boxPoints(rect)
            corners = np.array(box, dtype=np.float32)
            crop = self._warp_plate(image, corners)
            if crop.size == 0:
                continue
            detections.append(PlateDetection(crop=crop, corners=corners, confidence=0.5))
            break
        return detections

    def _affine_to_corners(self, affine: np.ndarray, width: int, height: int) -> np.ndarray:
        base = np.array([[0, 0], [width, 0], [width, height], [0, height]], dtype=np.float32)
        ones = np.ones((4, 1), dtype=np.float32)
        hom = np.hstack([base, ones])
        aff3 = np.vstack([affine, [0, 0, 1]])
        transformed = hom @ aff3.T
        return transformed[:, :2].astype(np.float32)

    def _warp_plate(self, image: np.ndarray, corners: np.ndarray) -> np.ndarray:
        if not self.perspective_correction:
            x, y, w, h = cv2.boundingRect(corners.astype(np.int32))
            return image[y : y + h, x : x + w]

        width_a = np.linalg.norm(corners[0] - corners[1])
        width_b = np.linalg.norm(corners[2] - corners[3])
        max_width = int(max(width_a, width_b))
        height_a = np.linalg.norm(corners[0] - corners[3])
        height_b = np.linalg.norm(corners[1] - corners[2])
        max_height = int(max(height_a, height_b))

        dst = np.array(
            [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
            dtype=np.float32,
        )
        matrix = cv2.getPerspectiveTransform(corners, dst)
        warped = cv2.warpPerspective(image, matrix, (max_width, max_height))

        if self.skew_correction:
            warped = self._deskew(warped)
        return warped

    @staticmethod
    def _deskew(image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        coords = np.column_stack(np.where(gray > 0))
        if len(coords) < 10:
            return image
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            image,
            matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
