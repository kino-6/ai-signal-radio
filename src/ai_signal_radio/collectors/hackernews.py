"""Hacker News collector using the public Algolia API."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ai_signal_radio.collectors.base import BaseCollector, CollectionError
from ai_signal_radio.models import NewsItem


class HackerNewsCollector(BaseCollector):
    def __init__(
        self,
        source_name: str,
        query: str = "AI OR LLM OR OpenAI OR Anthropic",
        timeout_seconds: int = 15,
    ) -> None:
        super().__init__(source_name)
        self.query = query
        self.timeout_seconds = timeout_seconds

    def collect(self, limit: int = 20) -> list[NewsItem]:
        params = urlencode({"query": self.query, "tags": "story", "hitsPerPage": str(limit)})
        url = f"https://hn.algolia.com/api/v1/search_by_date?{params}"
        try:
            request = Request(url, headers={"User-Agent": "ai-signal/0.1"})
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise CollectionError(f"failed to fetch Hacker News search results: {exc}") from exc

        return parse_hackernews_payload(payload, self.source_name)


def parse_hackernews_payload(payload: dict, source_name: str) -> list[NewsItem]:
    items: list[NewsItem] = []
    for hit in payload.get("hits", []):
        title = hit.get("title") or hit.get("story_title") or ""
        link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        points = int(hit.get("points") or 0)
        created_at = _parse_created_at(hit.get("created_at"))
        if title and link:
            items.append(
                NewsItem(
                    source=source_name,
                    source_type="hackernews",
                    title=title,
                    url=link,
                    summary=f"Hacker News discussion with {points} points.",
                    content=hit.get("comment_text") or hit.get("story_text") or "",
                    published_at=created_at,
                    tags=("hacker-news",),
                    metadata={"points": points, "object_id": hit.get("objectID")},
                )
            )
    return items


def _parse_created_at(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)
