from __future__ import annotations

import enum
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ViolationStatus(str, enum.Enum):
    NEW = "NEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    CASE_FILED = "CASE_FILED"


class Violation(Base):
    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(String(64), ForeignKey("cameras.camera_id"), index=True)
    violation_type: Mapped[str] = mapped_column(String(64), index=True)
    violation_title: Mapped[str] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date, index=True)
    time: Mapped[time] = mapped_column(Time)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    location_name: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    vehicle_number: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    annotated_evidence_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[ViolationStatus] = mapped_column(
        Enum(ViolationStatus), default=ViolationStatus.NEW, index=True
    )
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    tracking_key: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    evidence_records = relationship("Evidence", back_populates="violation")
