"""Simple deterministic ranking for MVP output order."""

from __future__ import annotations

from dataclasses import replace

from ai_signal_radio.models import NewsItem

KEYWORDS = (
    "model",
    "agent",
    "openai",
    "anthropic",
    "google",
    "hugging face",
    "ai",
    "llm",
)

OFFICIAL_SOURCES = ("openai", "anthropic", "google", "hugging face", "microsoft", "meta")


def rank_items(items: list[NewsItem], limit: int = 10) -> list[NewsItem]:
    scored = [replace(item, score=score_item(item)) for item in items]
    ordered = sorted(scored, key=_sort_key, reverse=True)
    return _select_with_source_diversity(ordered, limit)


def score_item(item: NewsItem) -> float:
    """Transparent MVP heuristic; higher score means more likely to be notable."""

    text = f"{item.title} {item.summary} {item.content} {' '.join(item.tags)}".lower()
    score = 0.0

    matched_keywords = [keyword for keyword in KEYWORDS if keyword in text]
    score += 2.0 * len(matched_keywords)

    source_text = f"{item.source} {item.url}".lower()
    if any(source in source_text for source in OFFICIAL_SOURCES):
        score += 4.0

    if item.source_type == "arxiv":
        score += 2.0

    points = item.metadata.get("points")
    if isinstance(points, int | float):
        score += min(float(points) / 100.0, 3.0)

    return round(score, 2)


def _select_with_source_diversity(items: list[NewsItem], limit: int) -> list[NewsItem]:
    if limit <= 0:
        return []
    if len(items) <= limit:
        return items

    selected: list[NewsItem] = []
    selected_ids: set[str] = set()

    min_by_type = _minimum_source_type_counts(items, limit)
    for source_type, minimum in min_by_type.items():
        for item in _items_of_type(items, source_type):
            if _source_type_count(selected, source_type) >= minimum:
                break
            _append_if_room(selected, selected_ids, item, limit)

    max_by_type = _maximum_source_type_counts(limit)
    for item in items:
        if item.id in selected_ids:
            continue
        type_limit = max_by_type.get(item.source_type)
        if type_limit is not None and _source_type_count(selected, item.source_type) >= type_limit:
            continue
        _append_if_room(selected, selected_ids, item, limit)
        if len(selected) >= limit:
            break

    # If diversity caps leave empty seats, fill them with the best remaining items.
    for item in items:
        if len(selected) >= limit:
            break
        _append_if_room(selected, selected_ids, item, limit)

    return sorted(selected, key=_sort_key, reverse=True)


def _minimum_source_type_counts(items: list[NewsItem], limit: int) -> dict[str, int]:
    minimums: dict[str, int] = {}
    if limit >= 3 and any(item.source_type == "arxiv" for item in items):
        minimums["arxiv"] = 1
    return minimums


def _maximum_source_type_counts(limit: int) -> dict[str, int]:
    if limit >= 4:
        return {"hackernews": max(1, min(3, limit - 1))}
    return {}


def _items_of_type(items: list[NewsItem], source_type: str) -> list[NewsItem]:
    return [item for item in items if item.source_type == source_type]


def _source_type_count(items: list[NewsItem], source_type: str) -> int:
    return sum(item.source_type == source_type for item in items)


def _append_if_room(
    selected: list[NewsItem], selected_ids: set[str], item: NewsItem, limit: int
) -> None:
    if len(selected) < limit and item.id not in selected_ids:
        selected.append(item)
        selected_ids.add(item.id)


def _sort_key(item: NewsItem) -> tuple[float, float]:
    return (item.score, item.published_at.timestamp())
