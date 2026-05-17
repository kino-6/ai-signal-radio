"""Simple deterministic ranking for MVP output order."""

from __future__ import annotations

from ai_signal_radio.models import NewsItem

KEYWORDS = (
    "agent",
    "ai",
    "artificial intelligence",
    "benchmark",
    "eval",
    "llm",
    "local",
    "model",
    "open source",
    "research",
    "tts",
)


def rank_items(items: list[NewsItem], limit: int = 10) -> list[NewsItem]:
    return sorted(items, key=_score_item, reverse=True)[:limit]


def _score_item(item: NewsItem) -> tuple[int, float]:
    text = f"{item.title} {item.summary} {' '.join(item.tags)}".lower()
    keyword_score = sum(1 for keyword in KEYWORDS if keyword in text)
    return (keyword_score, item.published_at.timestamp())
