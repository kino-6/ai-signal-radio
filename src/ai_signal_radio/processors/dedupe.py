"""Deduplication helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ai_signal_radio.models import NewsItem

TRACKING_PREFIXES = ("utm_",)
TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref"}


@dataclass(frozen=True)
class DuplicateGroup:
    reason: str
    selected_id: str
    duplicate_ids: tuple[str, ...]
    selected_title: str
    duplicate_titles: tuple[str, ...]
    key: str

    def to_dict(self) -> dict[str, object]:
        return {
            "reason": self.reason,
            "selected_id": self.selected_id,
            "duplicate_ids": list(self.duplicate_ids),
            "selected_title": self.selected_title,
            "duplicate_titles": list(self.duplicate_titles),
            "key": self.key,
        }


@dataclass(frozen=True)
class DedupeResult:
    input_count: int
    output_count: int
    selected_items: list[NewsItem]
    duplicate_groups: tuple[DuplicateGroup, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "input_count": self.input_count,
            "output_count": self.output_count,
            "duplicate_count": len(self.duplicate_groups),
            "duplicate_groups": [group.to_dict() for group in self.duplicate_groups],
        }

    @property
    def decisions(self) -> tuple[DuplicateGroup, ...]:
        """Backward-compatible name for older callers."""

        return self.duplicate_groups


def dedupe_items(items: list[NewsItem]) -> list[NewsItem]:
    """Deduplicate by canonical URL first, then normalized title."""

    return dedupe_items_with_report(items).selected_items


def dedupe_items_with_report(items: list[NewsItem]) -> DedupeResult:
    winners: list[NewsItem] = []
    groups: list[DuplicateGroup] = []
    for item in items:
        duplicate = _find_duplicate(winners, item)
        if duplicate is None:
            winners.append(item)
            continue

        duplicate_index, reason, key = duplicate
        current = winners[duplicate_index]
        if _quality_score(item) > _quality_score(current):
            winners[duplicate_index] = item
            groups.append(_duplicate_group(reason, key, selected=item, duplicates=(current,)))
        else:
            groups.append(_duplicate_group(reason, key, selected=current, duplicates=(item,)))

    winners = sorted(winners, key=lambda item: item.published_at, reverse=True)
    return DedupeResult(
        input_count=len(items),
        output_count=len(winners),
        selected_items=winners,
        duplicate_groups=tuple(groups),
    )


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


def _find_duplicate(winners: list[NewsItem], item: NewsItem) -> tuple[int, str, str] | None:
    item_url = canonical_url(item.url)
    item_title = normalize_title(item.title)
    for index, winner in enumerate(winners):
        if canonical_url(winner.url) == item_url:
            return index, "same_canonical_url", item_url
        if normalize_title(winner.title) == item_title:
            return index, "same_normalized_title", item_title
    return None


def _duplicate_group(
    reason: str,
    key: str,
    selected: NewsItem,
    duplicates: tuple[NewsItem, ...],
) -> DuplicateGroup:
    return DuplicateGroup(
        reason=reason,
        selected_id=selected.id,
        duplicate_ids=tuple(item.id for item in duplicates),
        selected_title=selected.title,
        duplicate_titles=tuple(item.title for item in duplicates),
        key=key,
    )


def _quality_score(item: NewsItem) -> tuple[int, int]:
    return (len(item.summary), len(item.tags))
