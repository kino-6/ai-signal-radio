"""Simple deterministic ranking for MVP output order."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from ai_signal_radio.config import RankerConfig
from ai_signal_radio.models import NewsItem
from ai_signal_radio.processors.topic_cluster import cluster_items

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


@dataclass
class _SelectionState:
    limit: int
    items: list[NewsItem] = field(default_factory=list)
    ids: set[str] = field(default_factory=set)
    cluster_counts: dict[str, int] = field(default_factory=dict)

    @property
    def has_room(self) -> bool:
        return len(self.items) < self.limit

    def source_count(self, source_type: str) -> int:
        return sum(item.source_type == source_type for item in self.items)

    def topic_cluster_count(self, item: NewsItem) -> int:
        cluster_id = _topic_cluster_id(item)
        if not cluster_id:
            return 0
        return self.cluster_counts.get(cluster_id, 0)

    def append(self, item: NewsItem) -> None:
        if not self.has_room or item.id in self.ids:
            return
        self.items.append(item)
        self.ids.add(item.id)
        cluster_id = _topic_cluster_id(item)
        if cluster_id:
            self.cluster_counts[cluster_id] = self.cluster_counts.get(cluster_id, 0) + 1


def rank_items(
    items: list[NewsItem],
    limit: int = 10,
    config: RankerConfig | None = None,
) -> list[NewsItem]:
    ranker_config = config or RankerConfig()
    scored = [_with_score_breakdown(item, ranker_config) for item in items]
    ordered = cluster_items(sorted(scored, key=_sort_key, reverse=True))
    return _select_with_source_diversity(ordered, limit, ranker_config)


def score_item(item: NewsItem, config: RankerConfig | None = None) -> float:
    """Transparent MVP heuristic; higher score means more likely to be notable."""

    return float(score_breakdown(item, config=config)["total"])


def score_breakdown(item: NewsItem, config: RankerConfig | None = None) -> dict[str, Any]:
    ranker_config = config or RankerConfig()
    text = f"{item.title} {item.summary} {item.content} {' '.join(item.tags)}".lower()

    matched_keywords = [keyword for keyword in KEYWORDS if keyword in text]
    keyword_score = ranker_config.keyword_bonus * len(matched_keywords)

    source_text = f"{item.source} {item.url}".lower()
    official_source_bonus = (
        ranker_config.official_source_bonus
        if any(source in source_text for source in OFFICIAL_SOURCES)
        else 0.0
    )

    research_bonus = ranker_config.research_bonus if item.source_type == "arxiv" else 0.0

    hn_points_bonus = 0.0
    points = item.metadata.get("points")
    if isinstance(points, int | float):
        hn_points_bonus = min(
            float(points) / ranker_config.hn_points_divisor,
            ranker_config.hn_points_cap,
        )

    total = round(keyword_score + official_source_bonus + research_bonus + hn_points_bonus, 2)
    return {
        "keyword_matches": matched_keywords,
        "keyword_score": round(keyword_score, 2),
        "official_source_bonus": round(official_source_bonus, 2),
        "research_bonus": round(research_bonus, 2),
        "hn_points_bonus": round(hn_points_bonus, 2),
        "total": total,
    }


def _with_score_breakdown(item: NewsItem, config: RankerConfig) -> NewsItem:
    breakdown = score_breakdown(item, config=config)
    metadata = dict(item.metadata)
    metadata["score_breakdown"] = breakdown
    return replace(item, score=float(breakdown["total"]), metadata=metadata)


def _select_with_source_diversity(
    items: list[NewsItem], limit: int, config: RankerConfig
) -> list[NewsItem]:
    if limit <= 0:
        return []
    if len(items) <= limit:
        return items

    state = _SelectionState(limit=limit)

    _satisfy_minimum_source_types(items, state, config)

    max_by_type = _maximum_source_type_counts(limit, config)
    _select_best_remaining(
        items,
        state,
        config,
        max_by_type=max_by_type,
        enforce_source_caps=True,
        enforce_topic_caps=True,
    )

    # First relax topic caps to fill seats with the best remaining items while
    # still preserving source balance. Deep-dive scripts can still see cluster
    # size in metadata even when the daily selection uses one representative.
    _select_best_remaining(
        items,
        state,
        config,
        max_by_type=max_by_type,
        enforce_source_caps=True,
        enforce_topic_caps=False,
    )

    # If source diversity caps leave empty seats, fill them with the best
    # remaining items only when there is no other source type to balance against.
    source_types = {item.source_type for item in items}
    if len(source_types) <= 1:
        _select_best_remaining(
            items,
            state,
            config,
            max_by_type=max_by_type,
            enforce_source_caps=False,
            enforce_topic_caps=False,
        )

    return sorted(state.items, key=_sort_key, reverse=True)


def _satisfy_minimum_source_types(
    items: list[NewsItem], state: _SelectionState, config: RankerConfig
) -> None:
    for source_type, minimum in _minimum_source_type_counts(items, state.limit, config).items():
        candidates = _items_of_type(items, source_type)
        _select_until_source_minimum(candidates, state, config, source_type, minimum, True)
        _select_until_source_minimum(candidates, state, config, source_type, minimum, False)


def _select_until_source_minimum(
    candidates: list[NewsItem],
    state: _SelectionState,
    config: RankerConfig,
    source_type: str,
    minimum: int,
    enforce_topic_caps: bool,
) -> None:
    for item in candidates:
        if state.source_count(source_type) >= minimum or not state.has_room:
            break
        if enforce_topic_caps and _topic_cap_reached(state, item, config):
            continue
        state.append(item)


def _select_best_remaining(
    items: list[NewsItem],
    state: _SelectionState,
    config: RankerConfig,
    max_by_type: dict[str, int],
    enforce_source_caps: bool,
    enforce_topic_caps: bool,
) -> None:
    for item in items:
        if not state.has_room:
            break
        if item.id in state.ids:
            continue
        if enforce_source_caps and _source_cap_reached(state, item, max_by_type):
            continue
        if enforce_topic_caps and _topic_cap_reached(state, item, config):
            continue
        state.append(item)


def _source_cap_reached(
    state: _SelectionState, item: NewsItem, max_by_type: dict[str, int]
) -> bool:
    type_limit = max_by_type.get(item.source_type)
    return type_limit is not None and state.source_count(item.source_type) >= type_limit


def _topic_cap_reached(state: _SelectionState, item: NewsItem, config: RankerConfig) -> bool:
    return state.topic_cluster_count(item) >= config.max_topic_cluster_items


def _minimum_source_type_counts(
    items: list[NewsItem], limit: int, config: RankerConfig
) -> dict[str, int]:
    minimums: dict[str, int] = {}
    if limit < 2:
        return minimums
    available_types = {item.source_type for item in items}
    for source_type, count in config.min_source_types.items():
        if source_type in available_types:
            minimums[source_type] = min(count, limit)
    return minimums


def _maximum_source_type_counts(limit: int, config: RankerConfig) -> dict[str, int]:
    if limit < 2:
        return {}
    return {
        source_type: max(1, min(count, limit))
        for source_type, count in config.max_source_types.items()
        if count > 0
    }


def _items_of_type(items: list[NewsItem], source_type: str) -> list[NewsItem]:
    return [item for item in items if item.source_type == source_type]


def _topic_cluster_id(item: NewsItem) -> str:
    cluster = item.metadata.get("topic_cluster")
    if not isinstance(cluster, dict):
        return ""
    return str(cluster.get("id", ""))


def _sort_key(item: NewsItem) -> tuple[float, float]:
    return (item.score, item.published_at.timestamp())
