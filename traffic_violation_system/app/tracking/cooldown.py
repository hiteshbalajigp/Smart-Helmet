"""Vehicle re-capture cooldown / deduplication service."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from app.config.settings import get_settings


@dataclass(frozen=True)
class VehicleIdentity:
    license_plate: str | None = None
    tracking_key: str | None = None

    def dedupe_key(self) -> str | None:
        if self.license_plate:
            return f"plate:{self.license_plate.strip().upper()}"
        if self.tracking_key:
            return f"track:{self.tracking_key}"
        return None


class VehicleCooldownService:
    """Prevents duplicate violation records within a configurable cooldown window."""

    def __init__(self, cooldown_seconds: int | None = None) -> None:
        settings = get_settings()
        self.cooldown_seconds = cooldown_seconds or settings.vehicle_violation_cooldown_seconds
        self._lock = threading.RLock()
        self._last_violation_at: dict[str, float] = {}

    def should_accept(self, identity: VehicleIdentity, *, now: float | None = None) -> bool:
        key = identity.dedupe_key()
        if not key:
            return True

        current = now if now is not None else time.time()
        with self._lock:
            last = self._last_violation_at.get(key)
            if last is None:
                return True
            return (current - last) >= self.cooldown_seconds

    def mark_violation(self, identity: VehicleIdentity, *, now: float | None = None) -> None:
        key = identity.dedupe_key()
        if not key:
            return
        current = now if now is not None else time.time()
        with self._lock:
            self._last_violation_at[key] = current

    def purge_expired(self, *, now: float | None = None) -> int:
        current = now if now is not None else time.time()
        removed = 0
        with self._lock:
            expired_keys = [
                key
                for key, ts in self._last_violation_at.items()
                if (current - ts) >= self.cooldown_seconds
            ]
            for key in expired_keys:
                del self._last_violation_at[key]
                removed += 1
        return removed
