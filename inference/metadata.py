"""GPS, timestamp, and device metadata collection."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GPSCoordinates:
    latitude: float
    longitude: float
    altitude: float | None = None
    speed_kmh: float | None = None


@dataclass
class ViolationMetadata:
    violation_id: str
    device_id: str
    timestamp: datetime
    gps: GPSCoordinates | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "violation_id": self.violation_id,
            "device_id": self.device_id,
            "timestamp": self.timestamp.isoformat(),
            "extra": self.extra,
        }
        if self.gps:
            data["gps"] = {
                "latitude": self.gps.latitude,
                "longitude": self.gps.longitude,
                "altitude": self.gps.altitude,
                "speed_kmh": self.gps.speed_kmh,
            }
        return data


class MetadataCollector:
    """Collect synchronized metadata for violations."""

    def __init__(
        self,
        device_id: str = "HELMET-001",
        gps_enabled: bool = True,
        gps_port: str = "/dev/ttyUSB0",
        gps_baudrate: int = 9600,
    ) -> None:
        self.device_id = device_id
        self.gps_enabled = gps_enabled
        self.gps_port = gps_port
        self.gps_baudrate = gps_baudrate
        self._last_gps: GPSCoordinates | None = None

    def get_current_gps(self) -> GPSCoordinates | None:
        if not self.gps_enabled:
            return None
        try:
            gps = self._read_gps_serial()
            if gps:
                self._last_gps = gps
            return self._last_gps
        except Exception as exc:
            logger.debug("GPS read failed, using last known: %s", exc)
            return self._last_gps

    def _read_gps_serial(self) -> GPSCoordinates | None:
        """Read NMEA GPS data from serial port (edge device)."""
        try:
            import serial

            with serial.Serial(self.gps_port, self.gps_baudrate, timeout=1) as ser:
                for _ in range(20):
                    line = ser.readline().decode("ascii", errors="ignore")
                    if line.startswith("$GPGGA") or line.startswith("$GPRMC"):
                        parts = line.split(",")
                        if len(parts) > 5 and parts[2] and parts[4]:
                            lat = self._parse_nmea_coord(parts[2], parts[3])
                            lon = self._parse_nmea_coord(parts[4], parts[5])
                            return GPSCoordinates(latitude=lat, longitude=lon)
        except ImportError:
            logger.debug("pyserial not installed; GPS disabled")
        except Exception as exc:
            logger.debug("Serial GPS unavailable: %s", exc)
        return None

    @staticmethod
    def _parse_nmea_coord(value: str, direction: str) -> float:
        if not value:
            return 0.0
        degrees = int(float(value) / 100)
        minutes = float(value) - degrees * 100
        decimal = degrees + minutes / 60.0
        if direction in {"S", "W"}:
            decimal *= -1
        return decimal

    def create_metadata(
        self,
        violation_id: str | None = None,
        timestamp: datetime | None = None,
        image_exif: dict[str, Any] | None = None,
    ) -> ViolationMetadata:
        vid = violation_id or str(uuid.uuid4())
        ts = timestamp or datetime.now(timezone.utc)
        extra: dict[str, Any] = {}
        if image_exif:
            extra["image_exif"] = image_exif
        return ViolationMetadata(
            violation_id=vid,
            device_id=self.device_id,
            timestamp=ts,
            gps=self.get_current_gps(),
            extra=extra,
        )
