"""Application configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from utils.config_loader import ConfigLoader


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HELMET_", env_file=".env", extra="ignore")

    api_prefix: str = "/api/v1"
    secret_key: str = "change-me-in-production"
    database_url: str = "sqlite+aiosqlite:///./database/helmet_local.db"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    evidence_storage: str = "evidence"


def _resolve_config_path() -> Path:
    override = os.environ.get("HELMET_CONFIG")
    if override:
        return Path(override)
    local_cfg = Path("configs/local.yaml")
    if local_cfg.exists() and os.environ.get("HELMET_USE_LOCAL", "1") == "1":
        return local_cfg
    return Path("configs/default.yaml")


@lru_cache
def get_settings() -> Settings:
    config = ConfigLoader(_resolve_config_path())
    backend_cfg = config.section("backend")
    db_cfg = config.section("database")
    return Settings(
        api_prefix=backend_cfg.get("api_prefix", "/api/v1"),
        secret_key=backend_cfg.get("secret_key", "change-me-in-production"),
        database_url=db_cfg.get("url"),
        cors_origins=backend_cfg.get("cors_origins", []),
        evidence_storage=backend_cfg.get("evidence_storage", "evidence"),
    )
