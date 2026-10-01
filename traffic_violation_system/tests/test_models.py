from datetime import datetime

from sqlalchemy.orm import Session

from app.database.models.camera import Camera
from app.database.models.violation import Violation, ViolationStatus
from app.schemas.violation_event import ViolationEvent
from app.services.violation_service import ViolationService


def test_create_violation_from_event(db_session: Session) -> None:
    camera = Camera(
        camera_id="CAM-01",
        camera_name="Main Gate",
        location_name="MG Road Junction",
        latitude=12.9716,
        longitude=77.5946,
    )
    db_session.add(camera)
    db_session.commit()

    event = ViolationEvent(
        camera_id="CAM-01",
        violation_type="RIDER_NO_HELMET",
        violation_title="Rider Not Wearing Helmet",
        captured_at=datetime(2026, 9, 30, 10, 0, 0),
        location_name="MG Road Junction",
        latitude=12.9716,
        longitude=77.5946,
        confidence=0.91,
    )

    violation = ViolationService().create_from_event(db_session, event)
    assert violation.id is not None
    assert violation.status == ViolationStatus.NEW
    assert violation.violation_title == "Rider Not Wearing Helmet"
