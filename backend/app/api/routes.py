"""REST API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.database import get_db
from backend.app.models.violation import Violation
from backend.app.schemas.violation import (
    DashboardStats,
    ViolationCreate,
    ViolationListResponse,
    ViolationResponse,
)
from backend.app.services.violation_service import ViolationService

router = APIRouter()
settings = get_settings()
service = ViolationService(evidence_root=settings.evidence_storage)


@router.post("/violations", response_model=ViolationResponse, status_code=201)
async def upload_violation(
    payload: ViolationCreate,
    db: AsyncSession = Depends(get_db),
) -> Violation:
    return await service.create(db, payload)


@router.get("/violations", response_model=ViolationListResponse)
async def get_violations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    violation_type: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> ViolationListResponse:
    items, total = await service.list_violations(db, skip, limit, violation_type)
    return ViolationListResponse(total=total, items=items)


@router.get("/violations/search", response_model=ViolationListResponse)
async def search_by_plate(
    plate: str = Query(..., min_length=2),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> ViolationListResponse:
    items, total = await service.search_by_plate(db, plate, skip, limit)
    return ViolationListResponse(total=total, items=items)


@router.get("/violations/{violation_id}", response_model=ViolationResponse)
async def get_violation(
    violation_id: str,
    db: AsyncSession = Depends(get_db),
) -> Violation:
    violation = await service.get_by_violation_id(db, violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    return violation


@router.get("/violations/{violation_id}/evidence/{evidence_type}")
async def download_evidence(
    violation_id: str,
    evidence_type: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    violation = await service.get_by_violation_id(db, violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    path_key = "snapshot" if evidence_type == "snapshot" else "video"
    stored_path = violation.snapshot_path if path_key == "snapshot" else violation.video_path
    resolved = service.resolve_evidence_path(stored_path)
    if not resolved or not resolved.exists():
        raise HTTPException(status_code=404, detail="Evidence file not found")

    media_type = "image/jpeg" if path_key == "snapshot" else "video/mp4"
    return FileResponse(resolved, media_type=media_type, filename=resolved.name)


@router.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_statistics(db: AsyncSession = Depends(get_db)) -> DashboardStats:
    return await service.dashboard_stats(db)
