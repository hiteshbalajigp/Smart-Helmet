from __future__ import annotations

from pydantic import BaseModel, Field


class CameraCreate(BaseModel):
    camera_id: str = Field(min_length=2, max_length=64)
    camera_name: str
    location_name: str
    latitude: float
    longitude: float
    usb_device_index: int | None = None
    usb_device_path: str | None = None
    is_authorized: bool = True


class CameraRead(BaseModel):
    id: int
    camera_id: str
    camera_name: str
    location_name: str
    latitude: float
    longitude: float
    usb_device_index: int | None
    is_authorized: bool
    is_active: bool

    model_config = {"from_attributes": True}
