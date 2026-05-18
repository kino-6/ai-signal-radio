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

    title: str
    url: str
    source: str
    source_type: str = "unknown"
    published_at: datetime | None = None
    collected_at: datetime | None = None
    summary: str = ""
    content: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    score: float = 0.0
    id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        source = self.source.strip()
        source_type = self.source_type.strip().lower() or "unknown"
        title = " ".join(self.title.split())
        url = self.url.strip()
        summary = self.summary.strip()
        content = self.content.strip()
        tags = tuple(dict.fromkeys(tag.strip().lower() for tag in self.tags if tag.strip()))
        published_at = ensure_aware_utc(self.published_at)
        collected_at = ensure_aware_utc(self.collected_at)
        item_id = self.id.strip() or _stable_id(source=source, url=url, title=title)

        if not source:
            raise ValueError("source is required")
        if not title:
            raise ValueError("title is required")
        if not url:
            raise ValueError("url is required")

        object.__setattr__(self, "source", source)
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "content", content)
        object.__setattr__(self, "published_at", published_at)
        object.__setattr__(self, "collected_at", collected_at)
        object.__setattr__(self, "tags", tags)
        object.__setattr__(self, "score", float(self.score))
        object.__setattr__(self, "id", item_id)

    @property
    def stable_id(self) -> str:
        return self.id

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "source_type": self.source_type,
            "published_at": self.published_at.isoformat(),
            "collected_at": self.collected_at.isoformat(),
            "summary": self.summary,
            "content": self.content,
            "tags": list(self.tags),
            "score": self.score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NewsItem":
        published_raw = data.get("published_at")
        published_at = (
            datetime.fromisoformat(published_raw) if isinstance(published_raw, str) else None
        )
        return cls(
            title=str(data.get("title", "")),
            url=str(data.get("url", "")),
            source=str(data.get("source", "")),
            source_type=str(data.get("source_type", "unknown")),
            published_at=published_at,
            collected_at=_parse_datetime(data.get("collected_at")),
            summary=str(data.get("summary", "")),
            content=str(data.get("content", "")),
            tags=tuple(str(tag) for tag in data.get("tags", ())),
            score=float(data.get("score", 0.0)),
            id=str(data.get("id", "")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class WikiNote:
    """A Markdown-ready wiki note derived from a news item."""

    title: str
    source: str
    source_url: str
    source_type: str
    published_at: datetime
    collected_at: datetime
    tags: tuple[str, ...]
    fact_summary: str
    interpretation: str
    action_items: tuple[str, ...]
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "source": self.source,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "published_at": self.published_at.isoformat(),
            "collected_at": self.collected_at.isoformat(),
            "tags": list(self.tags),
            "fact_summary": self.fact_summary,
            "interpretation": self.interpretation,
            "action_items": list(self.action_items),
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WikiNote":
        return cls(
            title=str(data["title"]),
            source=str(data.get("source", data.get("source_type", "unknown"))),
            source_url=str(data["source_url"]),
            source_type=str(data["source_type"]),
            published_at=ensure_aware_utc(_parse_datetime(data.get("published_at"))),
            collected_at=ensure_aware_utc(_parse_datetime(data.get("collected_at"))),
            tags=tuple(str(tag) for tag in data.get("tags", ())),
            fact_summary=str(data.get("fact_summary", "")),
            interpretation=str(data.get("interpretation", "")),
            action_items=tuple(str(item) for item in data.get("action_items", ())),
            score=float(data.get("score", 0.0)),
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


def _stable_id(source: str, url: str, title: str) -> str:
    payload = f"{source}\0{url}\0{title}".encode("utf-8")
    return sha256(payload).hexdigest()[:16]


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None
