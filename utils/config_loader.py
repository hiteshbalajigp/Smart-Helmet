"""Configuration loader with environment variable overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class ConfigLoader:
    """Load YAML configuration and support dot-notation access."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        if config_path is None:
            config_path = Path(__file__).resolve().parents[1] / "configs" / "default.yaml"
        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")
        with self.config_path.open("r", encoding="utf-8") as f:
            config: dict[str, Any] = yaml.safe_load(f) or {}
        return self._apply_env_overrides(config)

    def _apply_env_overrides(self, config: dict[str, Any]) -> dict[str, Any]:
        """Apply environment variable overrides (e.g. DATABASE__URL)."""
        prefix = "HELMET_"
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            parts = key[len(prefix) :].lower().split("__")
            node = config
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = self._cast_env_value(value)
        return config

    @staticmethod
    def _cast_env_value(value: str) -> Any:
        lowered = value.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value

    def get(self, key: str, default: Any = None) -> Any:
        """Get nested config value using dot notation."""
        node: Any = self._config
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    @property
    def raw(self) -> dict[str, Any]:
        return self._config

    def section(self, name: str) -> dict[str, Any]:
        section = self.get(name, {})
        if not isinstance(section, dict):
            raise ValueError(f"Config section '{name}' is not a mapping")
        return section
