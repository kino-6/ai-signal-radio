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
    speaker: int = 3
    speed_scale: float = 1.18
    pitch_scale: float = 0.0
    intonation_scale: float = 1.0
    pronunciation_profile: str | None = None


@dataclass(frozen=True)
class RankerConfig:
    keyword_bonus: float = 2.0
    official_source_bonus: float = 4.0
    research_bonus: float = 2.0
    hn_points_divisor: float = 100.0
    hn_points_cap: float = 3.0
    min_source_types: dict[str, int] = field(default_factory=lambda: {"arxiv": 1})
    max_source_types: dict[str, int] = field(default_factory=lambda: {"hackernews": 3})


@dataclass(frozen=True)
class AppConfig:
    sources: tuple[SourceConfig, ...] = field(default_factory=tuple)
    tts: TTSConfig = field(default_factory=TTSConfig)
    ranker: RankerConfig = field(default_factory=RankerConfig)


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    sources = tuple(_load_source(item) for item in raw.get("sources", []))
    tts = _load_tts(raw.get("tts", {}))
    ranker = _load_ranker(raw.get("ranker", {}))
    return AppConfig(sources=sources, tts=tts, ranker=ranker)


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
        speaker=int(raw.get("speaker", 3)),
        speed_scale=float(raw.get("speed_scale", raw.get("speed", 1.18))),
        pitch_scale=float(raw.get("pitch_scale", raw.get("pitch", 0.0))),
        intonation_scale=float(raw.get("intonation_scale", raw.get("intonation", 1.0))),
        pronunciation_profile=(
            str(raw["pronunciation_profile"]) if raw.get("pronunciation_profile") else None
        ),
    )


def _load_ranker(raw: dict[str, Any]) -> RankerConfig:
    return RankerConfig(
        keyword_bonus=float(raw.get("keyword_bonus", 2.0)),
        official_source_bonus=float(raw.get("official_source_bonus", 4.0)),
        research_bonus=float(raw.get("research_bonus", 2.0)),
        hn_points_divisor=float(raw.get("hn_points_divisor", 100.0)),
        hn_points_cap=float(raw.get("hn_points_cap", 3.0)),
        min_source_types=_int_mapping(raw.get("min_source_types"), {"arxiv": 1}),
        max_source_types=_int_mapping(raw.get("max_source_types"), {"hackernews": 3}),
    )


def _int_mapping(value: Any, default: dict[str, int]) -> dict[str, int]:
    if value is None:
        return dict(default)
    if not isinstance(value, dict):
        raise ValueError("source type diversity config must be a mapping")
    return {
        str(key).strip().lower(): max(0, int(count))
        for key, count in value.items()
        if str(key).strip()
    }
