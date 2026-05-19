"""Build deterministic wiki notes from processed news items."""

from __future__ import annotations

import re

from ai_signal_radio.config import TopicProfile
from ai_signal_radio.models import NewsItem, WikiNote
from ai_signal_radio.processors.headline import radio_title, rewrite_known_headline, shorten_headline


def note_from_item(item: NewsItem, topic_profile: TopicProfile | None = None) -> WikiNote:
    profile = topic_profile or TopicProfile()
    topic = item.title.rstrip(".")
    summary = item.summary or f"{item.source} が「{topic}」について報じています。"
    interpretation = (
        f"この項目は {item.source_type} 系の情報で、"
        f"{profile.interpretation_lens}に影響する可能性があります。"
    )
    dedupe_note = (
        dedupe_notes(item)
        or f"canonical_key={item.canonical_key}; content_hash={item.content_hash}."
    )
    score_reasons = score_reasons_from_item(item)
    cluster = topic_cluster_metadata(item)
    source_coverage = f"Single item from {item.source} ({item.source_type})."
    if cluster["size"] > 1:
        source_coverage = (
            f"Topic cluster '{cluster['label']}' includes {cluster['size']} related item(s) "
            f"from {', '.join(cluster['related_sources']) or item.source}."
        )
    return WikiNote(
        title=item.title,
        source=item.source,
        source_url=item.url,
        source_type=item.source_type,
        published_at=item.published_at,
        collected_at=item.collected_at,
        tags=item.tags or profile.default_tags,
        fact_summary=summary,
        interpretation=interpretation,
        action_items=profile.action_items,
        spoken_title=spoken_title_from_item(item),
        one_line_takeaway=one_line_takeaway_from_item(item, summary),
        why_it_matters=why_it_matters_from_item(item, interpretation, profile),
        listen_action="次に見るポイントは、元情報で具体的な変更点を確認することです。",
        score_reasons=score_reasons,
        source_coverage=source_coverage,
        dedupe_notes=dedupe_note,
        open_questions=("不明",),
        score=item.score,
        topic_cluster_id=cluster["id"],
        topic_cluster_label=cluster["label"],
        topic_cluster_size=cluster["size"],
        topic_cluster_representative=cluster["is_representative"],
        related_titles=cluster["related_titles"],
        related_sources=cluster["related_sources"],
    )


def spoken_title_from_item(item: NewsItem) -> str:
    title = radio_title(item.title)
    return rewrite_known_headline(title) or title


def one_line_takeaway_from_item(item: NewsItem, summary: str) -> str:
    if item.summary and contains_japanese(item.summary):
        return first_sentence(summary)
    return f"{item.source} が「{spoken_title_from_item(item)}」について報じています。"


def why_it_matters_from_item(
    item: NewsItem,
    interpretation: str,
    topic_profile: TopicProfile | None = None,
) -> str:
    profile = topic_profile or TopicProfile()
    if item.summary:
        return first_sentence(interpretation)
    return (
        f"{item.source_type} 系の情報として、"
        f"{profile.interpretation_lens}への影響を確認する価値があります。"
    )


def first_sentence(text: str) -> str:
    stripped = " ".join(text.split())
    if not stripped:
        return ""
    end_indexes = [index for index, char in enumerate(stripped) if char in "。.!?"]
    if end_indexes:
        return ensure_sentence(stripped[: end_indexes[0] + 1])
    return ensure_sentence(stripped)


def ensure_sentence(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if stripped[-1] in "。.!?！？":
        return stripped
    return f"{stripped}。"


def contains_japanese(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text))


def score_reasons_from_item(item: NewsItem) -> tuple[str, ...]:
    breakdown = item.metadata.get("score_breakdown")
    if not isinstance(breakdown, dict):
        return ("不明",)
    reasons: list[str] = []
    keywords = breakdown.get("keyword_matches")
    if isinstance(keywords, list) and keywords:
        reasons.append(f"keyword_matches={', '.join(str(keyword) for keyword in keywords)}")
    for key in ("keyword_score", "official_source_bonus", "research_bonus", "hn_points_bonus"):
        value = breakdown.get(key)
        if isinstance(value, int | float) and value:
            reasons.append(f"{key}={value}")
    return tuple(reasons) or ("不明",)


def dedupe_notes(item: NewsItem) -> str:
    dedupe = item.metadata.get("dedupe")
    if not isinstance(dedupe, dict):
        return ""
    duplicate_count = dedupe.get("duplicate_count")
    groups = dedupe.get("duplicate_groups")
    if not duplicate_count:
        return "No duplicates found for this selected item."
    if isinstance(groups, list):
        reasons = sorted(
            {str(group.get("reason", "unknown")) for group in groups if isinstance(group, dict)}
        )
        return f"Retained over {duplicate_count} duplicate(s): {', '.join(reasons) or '不明'}."
    return f"Retained over {duplicate_count} duplicate(s)."


def topic_cluster_metadata(item: NewsItem) -> dict[str, object]:
    cluster = item.metadata.get("topic_cluster")
    if not isinstance(cluster, dict):
        return {
            "id": "",
            "label": "",
            "size": 1,
            "is_representative": True,
            "related_titles": (),
            "related_sources": (item.source,),
        }
    return {
        "id": str(cluster.get("id", "")),
        "label": str(cluster.get("label", "")),
        "size": int(cluster.get("size", 1) or 1),
        "is_representative": bool(cluster.get("is_representative", True)),
        "related_titles": tuple(str(title) for title in cluster.get("related_titles", ())),
        "related_sources": tuple(str(source) for source in cluster.get("related_sources", ())),
    }
