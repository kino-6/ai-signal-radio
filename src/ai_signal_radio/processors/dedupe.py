"""Deduplication helpers."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ai_signal_radio.models import NewsItem

TRACKING_PREFIXES = ("utm_",)
TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref"}


def dedupe_items(items: list[NewsItem]) -> list[NewsItem]:
    """Deduplicate by canonical URL first, then normalized title."""

    winners: list[NewsItem] = []
    for item in items:
        duplicate_index = _find_duplicate(winners, item)
        if duplicate_index is None:
            winners.append(item)
        elif _quality_score(item) > _quality_score(winners[duplicate_index]):
            winners[duplicate_index] = item

    return sorted(winners, key=lambda item: item.published_at, reverse=True)


def canonical_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in TRACKING_PARAMS and not key.startswith(TRACKING_PREFIXES)
    ]
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            urlencode(query, doseq=True),
            "",
        )
    )


def normalize_title(title: str) -> str:
    normalized = re.sub(r"\W+", " ", title.lower())
    return " ".join(normalized.split())


def _find_duplicate(winners: list[NewsItem], item: NewsItem) -> int | None:
    item_url = canonical_url(item.url)
    item_title = normalize_title(item.title)
    for index, winner in enumerate(winners):
        if canonical_url(winner.url) == item_url or normalize_title(winner.title) == item_title:
            return index
    return None


def _quality_score(item: NewsItem) -> tuple[int, int]:
    return (len(item.summary), len(item.tags))
