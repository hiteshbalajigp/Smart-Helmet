"""Application configuration via environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Traffic Violation Detection System"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8000

    secret_key: str = Field(default="change-me-in-production", min_length=16)
    access_token_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"

    database_url: str = f"sqlite:///{(PROJECT_ROOT / 'data' / 'database' / 'traffic_violations.db').as_posix()}"

    log_level: str = "INFO"
    log_dir: Path = PROJECT_ROOT / "logs"

    evidence_dir: Path = PROJECT_ROOT / "data" / "evidence"
    annotated_evidence_dir: Path = PROJECT_ROOT / "data" / "annotated"

    yolo_weights_path: Path = PROJECT_ROOT / "model_weights" / "yolo" / "best.pt"
    wpod_weights_path: Path = PROJECT_ROOT / "model_weights" / "wpod" / "wpod-net.h5"
    paddleocr_lang: str = "en"

    vehicle_violation_cooldown_seconds: int = 3600
    camera_scan_max_index: int = 10
    frame_buffer_size: int = 30

    camera_id: str = "helmet-cam-01"
    camera_index: int = 0
    camera_width: int = 1920
    camera_height: int = 1080
    camera_fps: int = 30
    camera_backend: str = "auto"
    camera_reconnect_enabled: bool = True
    camera_reconnect_delay: float = 2.0

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    notification_enabled: bool = False

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def ensure_directories(self) -> None:
        for path in (
            self.log_dir,
            self.evidence_dir,
            self.annotated_evidence_dir,
            PROJECT_ROOT / "data" / "database",
            PROJECT_ROOT / "model_weights" / "yolo",
            PROJECT_ROOT / "model_weights" / "wpod",
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
