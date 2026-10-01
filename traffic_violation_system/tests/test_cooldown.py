from app.tracking.cooldown import VehicleCooldownService, VehicleIdentity


def test_cooldown_blocks_repeat_plate_within_window() -> None:
    service = VehicleCooldownService(cooldown_seconds=3600)
    identity = VehicleIdentity(license_plate="KA01AB1234")

    assert service.should_accept(identity, now=1000.0) is True
    service.mark_violation(identity, now=1000.0)
    assert service.should_accept(identity, now=2000.0) is False
    assert service.should_accept(identity, now=5000.0) is True


def test_tracking_key_fallback() -> None:
    service = VehicleCooldownService(cooldown_seconds=60)
    identity = VehicleIdentity(tracking_key="track-abc")
    assert service.should_accept(identity, now=10.0) is True
    service.mark_violation(identity, now=10.0)
    assert service.should_accept(identity, now=20.0) is False
