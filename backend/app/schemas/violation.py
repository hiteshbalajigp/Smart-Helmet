"""Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GPSPayload(BaseModel):
    latitude: float
    longitude: float
    altitude: float | None = None
    speed_kmh: float | None = None


class ViolationCreate(BaseModel):
    violation_id: str
    violation_type: str
    timestamp: datetime
    track_id: int
    confidence: float = Field(ge=0.0, le=1.0)
    plate_text: str | None = None
    device_id: str
    gps: GPSPayload | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, str] = Field(default_factory=dict)


class ViolationResponse(BaseModel):
    id: int
    violation_id: str
    violation_type: str
    plate_text: str | None
    confidence: float
    device_id: str
    latitude: float | None
    longitude: float | None
    timestamp: datetime
    snapshot_path: str | None
    video_path: str | None
    metadata_json: str | None

    model_config = {"from_attributes": True}


class ViolationListResponse(BaseModel):
    total: int
    items: list[ViolationResponse]


class DashboardStats(BaseModel):
    total_violations: int
    no_helmet_count: int
    triple_riding_count: int
    unique_plates: int
    violations_by_day: dict[str, int]
    violations_by_type: dict[str, int]
