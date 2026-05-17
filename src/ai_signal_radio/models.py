"""Core data models for the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware_utc(value: datetime | None) -> datetime:
    if value is None:
        return utc_now()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class NewsItem:
    """A normalized news item collected from any source."""

    source: str
    title: str
    url: str
    summary: str = ""
    published_at: datetime | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        source = self.source.strip()
        title = " ".join(self.title.split())
        url = self.url.strip()
        summary = self.summary.strip()
        tags = tuple(dict.fromkeys(tag.strip().lower() for tag in self.tags if tag.strip()))

        if not source:
            raise ValueError("source is required")
        if not title:
            raise ValueError("title is required")
        if not url:
            raise ValueError("url is required")

        object.__setattr__(self, "source", source)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "published_at", ensure_aware_utc(self.published_at))
        object.__setattr__(self, "tags", tags)

    @property
    def stable_id(self) -> str:
        payload = f"{self.source}\0{self.url}\0{self.title}".encode("utf-8")
        return sha256(payload).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.stable_id,
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "published_at": self.published_at.isoformat(),
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NewsItem":
        published_raw = data.get("published_at")
        published_at = (
            datetime.fromisoformat(published_raw) if isinstance(published_raw, str) else None
        )
        return cls(
            source=str(data.get("source", "")),
            title=str(data.get("title", "")),
            url=str(data.get("url", "")),
            summary=str(data.get("summary", "")),
            published_at=published_at,
            tags=tuple(str(tag) for tag in data.get("tags", ())),
        )


@dataclass(frozen=True)
class PipelineResult:
    collected_count: int
    deduped_count: int
    selected_count: int
    raw_path: str
    wiki_path: str
    script_path: str
    audio_path: str | None = None
