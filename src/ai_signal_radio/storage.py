"""Filesystem storage helpers."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_signal_radio.models import NewsItem
from ai_signal_radio.processors.dedupe import DedupeResult


def ensure_data_dirs(data_dir: Path) -> None:
    for child in ("raw", "processed", "wiki", "scripts", "audio"):
        (data_dir / child).mkdir(parents=True, exist_ok=True)


def timestamp_slug(now: datetime | None = None) -> str:
    value = now or datetime.now(timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.strftime("%Y%m%dT%H%M%S%fZ")


def date_slug(now: datetime | None = None) -> str:
    value = now or datetime.now(timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.strftime("%Y-%m-%d")


def save_raw_items(
    items: list[NewsItem],
    data_dir: Path,
    now: datetime | None = None,
    run_id: str | None = None,
) -> Path:
    ensure_data_dirs(data_dir)
    slug = run_id or timestamp_slug(now)
    archive_path = data_dir / "raw" / f"{slug}-items.json"
    latest_path = data_dir / "raw" / "latest.json"
    payload = [item.to_dict() for item in items]
    archive_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    shutil.copyfile(archive_path, latest_path)
    return latest_path


def save_processed_items(
    items: list[NewsItem],
    data_dir: Path,
    run_id: str,
    now: datetime | None = None,
) -> Path:
    ensure_data_dirs(data_dir)
    day_dir = data_dir / "processed" / date_slug(now)
    day_dir.mkdir(parents=True, exist_ok=True)
    archive_path = day_dir / f"{run_id}.json"
    latest_path = data_dir / "processed" / "latest.json"
    payload = [item.to_dict() for item in items]
    archive_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    shutil.copyfile(archive_path, latest_path)
    return latest_path


def save_run_metadata(
    metadata: dict[str, Any],
    data_dir: Path,
    run_id: str,
    now: datetime | None = None,
) -> Path:
    ensure_data_dirs(data_dir)
    day_dir = data_dir / "processed" / date_slug(now)
    day_dir.mkdir(parents=True, exist_ok=True)
    archive_path = day_dir / f"{run_id}-metadata.json"
    latest_path = data_dir / "processed" / "latest-metadata.json"
    archive_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    shutil.copyfile(archive_path, latest_path)
    return latest_path


def save_dedupe_report(report: DedupeResult, data_dir: Path, run_id: str) -> Path:
    ensure_data_dirs(data_dir)
    archive_path = data_dir / "raw" / f"{run_id}-dedupe.json"
    latest_path = data_dir / "raw" / "latest-dedupe.json"
    archive_path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    shutil.copyfile(archive_path, latest_path)
    return latest_path


def load_raw_items(path: Path) -> list[NewsItem]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [NewsItem.from_dict(item) for item in raw]
