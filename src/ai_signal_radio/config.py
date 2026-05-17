"""Configuration loading for source and TTS settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SourceConfig:
    name: str
    type: str
    enabled: bool = True
    url: str | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TTSConfig:
    enabled: bool = False
    endpoint: str = "http://127.0.0.1:50021"
    speaker: int = 1


@dataclass(frozen=True)
class AppConfig:
    sources: tuple[SourceConfig, ...] = field(default_factory=tuple)
    tts: TTSConfig = field(default_factory=TTSConfig)


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    sources = tuple(_load_source(item) for item in raw.get("sources", []))
    tts = _load_tts(raw.get("tts", {}))
    return AppConfig(sources=sources, tts=tts)


def _load_source(raw: dict[str, Any]) -> SourceConfig:
    params = raw.get("params") or {}
    if not isinstance(params, dict):
        raise ValueError("source params must be a mapping")
    return SourceConfig(
        name=str(raw.get("name", "")).strip(),
        type=str(raw.get("type", "")).strip().lower(),
        enabled=bool(raw.get("enabled", True)),
        url=str(raw["url"]).strip() if raw.get("url") else None,
        params=params,
    )


def _load_tts(raw: dict[str, Any]) -> TTSConfig:
    return TTSConfig(
        enabled=bool(raw.get("enabled", False)),
        endpoint=str(raw.get("endpoint", "http://127.0.0.1:50021")).rstrip("/"),
        speaker=int(raw.get("speaker", 1)),
    )
