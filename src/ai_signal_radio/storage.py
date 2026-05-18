"""Filesystem storage helpers."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from ai_signal_radio.models import NewsItem


def ensure_data_dirs(data_dir: Path) -> None:
    for child in ("raw", "wiki", "scripts", "audio"):
        (data_dir / child).mkdir(parents=True, exist_ok=True)


def timestamp_slug(now: datetime | None = None) -> str:
    value = now or datetime.now(timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.strftime("%Y%m%dT%H%M%SZ")


def date_slug(now: datetime | None = None) -> str:
    value = now or datetime.now(timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.strftime("%Y-%m-%d")


def save_raw_items(items: list[NewsItem], data_dir: Path, now: datetime | None = None) -> Path:
    ensure_data_dirs(data_dir)
    archive_path = data_dir / "raw" / f"{timestamp_slug(now)}-items.json"
    latest_path = data_dir / "raw" / "latest.json"
    payload = [item.to_dict() for item in items]
    archive_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    shutil.copyfile(archive_path, latest_path)
    return latest_path


def load_raw_items(path: Path) -> list[NewsItem]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [NewsItem.from_dict(item) for item in raw]
