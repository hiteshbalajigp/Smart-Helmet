"""Locked violation titles and internal type keys."""

from __future__ import annotations

import enum


class ViolationType(str, enum.Enum):
    RIDER_NO_HELMET = "RIDER_NO_HELMET"
    PILLION_NO_HELMET = "PILLION_NO_HELMET"
    BOTH_NO_HELMET = "BOTH_NO_HELMET"
    CAP_HALF_HELMET = "CAP_HALF_HELMET"
    TRIPLE_RIDING = "TRIPLE_RIDING"


class ViolationTitle(str, enum.Enum):
    RIDER_NOT_WEARING_HELMET = "Rider Not Wearing Helmet"
    PILLION_NOT_WEARING_HELMET = "Pillion Rider Not Wearing Helmet"
    BOTH_NOT_WEARING_HELMET = "Rider and Pillion Rider Not Wearing Helmet"
    CAP_HALF_HELMET = "Wearing Cap / Half Helmet"
    TRIPLE_RIDING = "Triple Riding"


VIOLATION_TYPE_TO_TITLE: dict[ViolationType, ViolationTitle] = {
    ViolationType.RIDER_NO_HELMET: ViolationTitle.RIDER_NOT_WEARING_HELMET,
    ViolationType.PILLION_NO_HELMET: ViolationTitle.PILLION_NOT_WEARING_HELMET,
    ViolationType.BOTH_NO_HELMET: ViolationTitle.BOTH_NOT_WEARING_HELMET,
    ViolationType.CAP_HALF_HELMET: ViolationTitle.CAP_HALF_HELMET,
    ViolationType.TRIPLE_RIDING: ViolationTitle.TRIPLE_RIDING,
}
