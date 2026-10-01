"""Violation business logic."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.violation import Violation
from backend.app.schemas.violation import DashboardStats, ViolationCreate


class ViolationService:
    def __init__(self, evidence_root: str = "evidence") -> None:
        self.evidence_root = Path(evidence_root)

    async def create(self, db: AsyncSession, payload: ViolationCreate) -> Violation:
        violation = Violation(
            violation_id=payload.violation_id,
            violation_type=payload.violation_type,
            plate_text=payload.plate_text,
            confidence=payload.confidence,
            device_id=payload.device_id,
            latitude=payload.gps.latitude if payload.gps else None,
            longitude=payload.gps.longitude if payload.gps else None,
            timestamp=payload.timestamp,
            snapshot_path=payload.evidence.get("snapshot"),
            video_path=payload.evidence.get("video"),
            metadata_json=json.dumps(payload.metadata),
        )
        db.add(violation)
        await db.commit()
        await db.refresh(violation)
        return violation

    async def list_violations(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        violation_type: str | None = None,
    ) -> tuple[list[Violation], int]:
        query = select(Violation)
        count_query = select(func.count(Violation.id))
        if violation_type:
            query = query.where(Violation.violation_type == violation_type)
            count_query = count_query.where(Violation.violation_type == violation_type)

        total = (await db.execute(count_query)).scalar_one()
        result = await db.execute(query.order_by(Violation.timestamp.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def search_by_plate(
        self,
        db: AsyncSession,
        plate: str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Violation], int]:
        pattern = f"%{plate.upper()}%"
        query = select(Violation).where(Violation.plate_text.ilike(pattern))
        count_query = select(func.count(Violation.id)).where(Violation.plate_text.ilike(pattern))
        total = (await db.execute(count_query)).scalar_one()
        result = await db.execute(query.order_by(Violation.timestamp.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def get_by_violation_id(self, db: AsyncSession, violation_id: str) -> Violation | None:
        result = await db.execute(select(Violation).where(Violation.violation_id == violation_id))
        return result.scalar_one_or_none()

    async def dashboard_stats(self, db: AsyncSession) -> DashboardStats:
        violations = (await db.execute(select(Violation))).scalars().all()
        by_type = Counter(v.violation_type for v in violations)
        by_day = Counter(v.timestamp.date().isoformat() for v in violations)
        plates = {v.plate_text for v in violations if v.plate_text}
        return DashboardStats(
            total_violations=len(violations),
            no_helmet_count=by_type.get("no_helmet", 0),
            triple_riding_count=by_type.get("triple_riding", 0),
            unique_plates=len(plates),
            violations_by_day=dict(by_day),
            violations_by_type=dict(by_type),
        )

    def resolve_evidence_path(self, path: str | None) -> Path | None:
        if not path:
            return None
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = self.evidence_root / resolved
        return resolved if resolved.exists() else Path(path) if Path(path).exists() else None
