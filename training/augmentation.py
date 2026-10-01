"""Albumentations-based augmentation pipeline."""

from __future__ import annotations

from typing import Any

import albumentations as A
import cv2
import numpy as np


class AugmentationPipeline:
    """Configurable augmentation for object detection training."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        config = config or {}
        self.transform = A.Compose(
            [
                A.Rotate(limit=config.get("rotation_limit", 15), p=0.5),
                A.RandomBrightnessContrast(
                    brightness_limit=config.get("brightness_limit", 0.3),
                    contrast_limit=config.get("contrast_limit", 0.3),
                    p=0.6,
                ),
                A.MotionBlur(blur_limit=config.get("motion_blur_limit", 7), p=0.3),
                A.GaussNoise(
                    var_limit=tuple(config.get("gaussian_noise_var", [10, 50])),
                    p=0.3,
                ),
                A.RandomRain(
                    slant_lower=-10,
                    slant_upper=10,
                    drop_length=20,
                    drop_width=1,
                    drop_color=(200, 200, 200),
                    blur_value=3,
                    brightness_coefficient=0.9,
                    rain_type="drizzle",
                    p=config.get("rain_intensity", 0.3),
                ),
                A.RandomShadow(
                    shadow_roi=(0, 0.5, 1, 1),
                    num_shadows_lower=1,
                    num_shadows_upper=2,
                    shadow_dimension=5,
                    p=config.get("shadow_intensity", 0.4),
                ),
                A.RandomGamma(gamma_limit=(50, 120), p=config.get("low_light_factor", 0.4)),
                A.Perspective(
                    scale=(0.02, config.get("perspective_scale", 0.05)),
                    p=0.4,
                ),
            ],
            bbox_params=A.BboxParams(format="pascal_voc", label_fields=["class_labels"]),
        )

    def __call__(
        self,
        image: np.ndarray,
        bboxes: list[list[float]],
        class_ids: list[int],
    ) -> tuple[np.ndarray, list[list[float]], list[int]]:
        if not bboxes:
            augmented = self.transform(image=image, bboxes=[], class_labels=[])
            return augmented["image"], [], []

        augmented = self.transform(image=image, bboxes=bboxes, class_labels=class_ids)
        return augmented["image"], augmented["bboxes"], augmented["class_labels"]


def apply_mixup(
    image_a: np.ndarray,
    image_b: np.ndarray,
    alpha: float = 0.5,
) -> np.ndarray:
    """Simple MixUp augmentation for unlabeled or mosaic pre-processing."""
    return cv2.addWeighted(image_a, alpha, image_b, 1 - alpha, 0)


def apply_mosaic(
    images: list[np.ndarray],
    target_size: int = 640,
) -> np.ndarray:
    """Create 2x2 mosaic from four images."""
    if len(images) < 4:
        raise ValueError("Mosaic requires at least 4 images")

    mosaic = np.zeros((target_size, target_size, 3), dtype=np.uint8)
    half = target_size // 2
    resized = [cv2.resize(img, (half, half)) for img in images[:4]]
    mosaic[:half, :half] = resized[0]
    mosaic[:half, half:] = resized[1]
    mosaic[half:, :half] = resized[2]
    mosaic[half:, half:] = resized[3]
    return mosaic
