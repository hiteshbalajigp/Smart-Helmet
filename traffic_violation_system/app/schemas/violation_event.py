"""Internal pipeline event emitted after violation decision (pre-persistence)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class ViolationEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    camera_id: str
    violation_type: str
    violation_title: str
    captured_at: datetime
    location_name: str
    latitude: float
    longitude: float
    vehicle_number: str | None = None
    tracking_key: str | None = None
    confidence: float = 0.0
    evidence_frame_path: str | None = None
    annotated_frame_path: str | None = None
    metadata: dict[str, str | float | int | bool] = Field(default_factory=dict)
