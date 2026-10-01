"""Unit tests for Indian plate OCR validation."""

import numpy as np
import pytest

from inference.plate_ocr import PlateOCR


@pytest.fixture
def ocr():
    return PlateOCR()


def test_indian_plate_validation(ocr):
    assert ocr._validate_indian_plate("DL01AB1234") is True
    assert ocr._validate_indian_plate("MH12DE1432") is True
    assert ocr._validate_indian_plate("INVALID") is False


def test_character_correction(ocr):
    corrected = ocr._correct_characters("DL01AB1234")
    assert corrected == "DL01AB1234"


def test_recognize_empty_image(ocr):
    blank = np.zeros((40, 120, 3), dtype=np.uint8)
    result = ocr.recognize(blank)
    assert result.is_valid is False
