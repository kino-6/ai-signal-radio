"""Reusable run profile import/export helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

RUN_PROFILE_VERSION = 1

RUN_PROFILE_KEYS = {
    "version",
    "name",
    "config",
    "dataDir",
    "topic",
    "editorialSkill",
    "limit",
    "collectLimit",
    "source",
    "summarizer",
    "ollamaModel",
    "ollamaUrl",
    "scriptStyle",
    "editorialModel",
    "editorialUrl",
}

SCRIPT_STYLES = {"short", "standard", "detailed", "briefing", "dialogue"}
SUMMARIZERS = {"placeholder", "ollama"}


@dataclass(frozen=True)
class RunProfile:
    name: str
    version: int = RUN_PROFILE_VERSION
    config: str | None = None
    data_dir: str | None = None
    topic: str | None = None
    editorial_skill: str | None = None
    limit: int | None = None
    collect_limit: int | None = None
    source: tuple[str, ...] = ()
    summarizer: str | None = None
    ollama_model: str | None = None
    ollama_url: str | None = None
    script_style: str | None = None
    editorial_model: str | None = None
    editorial_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "version": self.version,
            "name": self.name,
        }
        optional_fields: tuple[tuple[str, object | None], ...] = (
            ("config", self.config),
            ("dataDir", self.data_dir),
            ("topic", self.topic),
            ("editorialSkill", self.editorial_skill),
            ("limit", self.limit),
            ("collectLimit", self.collect_limit),
            ("summarizer", self.summarizer),
            ("ollamaModel", self.ollama_model),
            ("ollamaUrl", self.ollama_url),
            ("scriptStyle", self.script_style),
            ("editorialModel", self.editorial_model),
            ("editorialUrl", self.editorial_url),
        )
        for key, value in optional_fields:
            if value is not None:
                payload[key] = value
        if self.source:
            payload["source"] = list(self.source)
        return payload


@dataclass(frozen=True)
class RunProfileDocument:
    profile: RunProfile
    warnings: tuple[str, ...] = ()


def load_run_profile(path: Path, strict: bool = False) -> RunProfileDocument:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"run profile must be valid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("run profile must be a JSON object")

    unknown = tuple(sorted(set(raw) - RUN_PROFILE_KEYS))
    if unknown and strict:
        raise ValueError(f"run profile contains unknown keys: {', '.join(unknown)}")

    warnings = tuple(f"unknown profile key ignored: {key}" for key in unknown)
    version = int(raw.get("version", RUN_PROFILE_VERSION))
    if version != RUN_PROFILE_VERSION:
        raise ValueError(f"unsupported run profile version: {version}")

    profile = RunProfile(
        version=version,
        name=_required_str(raw.get("name"), "name"),
        config=_optional_str(raw.get("config"), "config"),
        data_dir=_optional_str(raw.get("dataDir"), "dataDir"),
        topic=_optional_str(raw.get("topic"), "topic"),
        editorial_skill=_optional_str(raw.get("editorialSkill"), "editorialSkill"),
        limit=_optional_positive_int(raw.get("limit"), "limit"),
        collect_limit=_optional_positive_int(raw.get("collectLimit"), "collectLimit"),
        source=_str_tuple(raw.get("source"), "source"),
        summarizer=_choice(raw.get("summarizer"), "summarizer", SUMMARIZERS),
        ollama_model=_optional_str(raw.get("ollamaModel"), "ollamaModel"),
        ollama_url=_optional_str(raw.get("ollamaUrl"), "ollamaUrl"),
        script_style=_choice(raw.get("scriptStyle"), "scriptStyle", SCRIPT_STYLES),
        editorial_model=_optional_str(raw.get("editorialModel"), "editorialModel"),
        editorial_url=_optional_str(raw.get("editorialUrl"), "editorialUrl"),
    )
    return RunProfileDocument(profile=profile, warnings=warnings)


def write_run_profile(path: Path, profile: RunProfile) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(profile.to_dict(), ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return path


def _required_str(value: Any, field_name: str) -> str:
    text = _optional_str(value, field_name)
    if text is None:
        raise ValueError(f"run profile requires {field_name}")
    return text


def _optional_str(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"run profile {field_name} must be a string")
    text = value.strip()
    return text or None


def _optional_positive_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    count = int(value)
    if count < 1:
        raise ValueError(f"run profile {field_name} must be greater than zero")
    return count


def _str_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, list):
        values = tuple(value)
    else:
        raise ValueError(f"run profile {field_name} must be a string or list")
    cleaned = tuple(str(item).strip() for item in values if str(item).strip())
    return cleaned


def _choice(value: Any, field_name: str, choices: set[str]) -> str | None:
    text = _optional_str(value, field_name)
    if text is None:
        return None
    if text not in choices:
        raise ValueError(f"run profile {field_name} must be one of: {', '.join(sorted(choices))}")
    return text
