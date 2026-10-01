"""Common exception types."""

from __future__ import annotations


class HelmetSystemError(Exception):
    """Base exception for the smart helmet system."""


class ConfigurationError(HelmetSystemError):
    """Invalid or missing configuration."""


class ModelLoadError(HelmetSystemError):
    """Failed to load ML model."""


class InferenceError(HelmetSystemError):
    """Runtime inference failure."""


class EvidenceCaptureError(HelmetSystemError):
    """Evidence buffer or save failure."""


class OCRValidationError(HelmetSystemError):
    """License plate OCR validation failure."""
