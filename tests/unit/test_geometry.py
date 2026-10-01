"""Unit tests for geometry utilities."""

import pytest

from utils.geometry import BoundingBox, associate_by_iou, clip_bbox


def test_bbox_iou_full_overlap():
    a = BoundingBox(0, 0, 10, 10)
    b = BoundingBox(0, 0, 10, 10)
    assert a.iou(b) == pytest.approx(1.0)


def test_bbox_iou_no_overlap():
    a = BoundingBox(0, 0, 10, 10)
    b = BoundingBox(20, 20, 30, 30)
    assert a.iou(b) == 0.0


def test_clip_bbox():
    bbox = BoundingBox(-5, -5, 100, 100)
    clipped = clip_bbox(bbox, 50, 50)
    assert clipped.x1 == 0
    assert clipped.y1 == 0
    assert clipped.x2 == 50
    assert clipped.y2 == 50


def test_associate_by_iou():
    motorcycles = [BoundingBox(0, 0, 100, 100)]
    riders = [BoundingBox(10, 10, 40, 80), BoundingBox(200, 200, 220, 240)]
    assoc = associate_by_iou(motorcycles, riders, iou_threshold=0.01)
    assert len(assoc[0]) == 1
