from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models.evidence import Evidence
from app.database.models.violation import Violation, ViolationStatus
from app.schemas.violation_event import ViolationEvent


class ViolationService:
    def create_from_event(self, db: Session, event: ViolationEvent) -> Violation:
        violation = Violation(
            camera_id=event.camera_id,
            violation_type=event.violation_type,
            violation_title=event.violation_title,
            date=event.captured_at.date(),
            time=event.captured_at.time().replace(microsecond=0),
            timestamp=event.captured_at,
            location_name=event.location_name,
            latitude=event.latitude,
            longitude=event.longitude,
            vehicle_number=event.vehicle_number,
            confidence=event.confidence,
            evidence_path=event.evidence_frame_path,
            annotated_evidence_path=event.annotated_frame_path,
            tracking_key=event.tracking_key,
            status=ViolationStatus.NEW,
        )
        db.add(violation)
        db.flush()

        if event.evidence_frame_path:
            db.add(
                Evidence(
                    violation_id=violation.id,
                    original_path=event.evidence_frame_path,
                    annotated_path=event.annotated_frame_path,
                )
            )

        db.commit()
        db.refresh(violation)
        return violation
