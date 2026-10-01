from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_roles
from app.database.models.user import User, UserRole
from app.detection.yolo_loader import YOLODetector
from app.ocr.paddle_loader import PaddleOCRService
from app.plate_detection.wpod_loader import WPODPlateDetector

router = APIRouter()


@router.get("/model-status")
def model_status(
    _: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.TRAFFIC_POLICE))],
) -> dict[str, dict[str, str | bool]]:
    yolo = YOLODetector().load()
    wpod = WPODPlateDetector().load()
    ocr = PaddleOCRService().load()
    return {
        "yolo": {"loaded": yolo.loaded, "message": yolo.message},
        "wpod": {"loaded": wpod.loaded, "message": wpod.message},
        "paddleocr": {"loaded": ocr.loaded, "message": ocr.message},
    }
