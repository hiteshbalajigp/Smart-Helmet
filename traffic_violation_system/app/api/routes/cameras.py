from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user, require_roles
from app.camera.manager import CameraManager
from app.database.models.camera import Camera
from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.schemas.camera import CameraCreate, CameraRead

router = APIRouter()
camera_manager = CameraManager()


@router.get("/discover")
def discover_cameras(
    _: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.TRAFFIC_POLICE))],
) -> list[dict[str, str | int | bool]]:
    discovered = camera_manager.discover_usb_cameras()
    return [
        {"device_index": item.device_index, "backend": item.backend, "opened": item.opened}
        for item in discovered
    ]


@router.post("", response_model=CameraRead, status_code=status.HTTP_201_CREATED)
def register_camera(
    payload: CameraCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> Camera:
    if db.query(Camera).filter(Camera.camera_id == payload.camera_id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="camera_id already exists")

    camera = Camera(**payload.model_dump())
    db.add(camera)
    db.commit()
    db.refresh(camera)

    if payload.usb_device_index is not None:
        camera_manager.register_authorized_camera(payload.camera_id, payload.usb_device_index)

    return camera


@router.get("", response_model=list[CameraRead])
def list_cameras(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> list[Camera]:
    return db.query(Camera).order_by(Camera.camera_id.asc()).all()
