"""Build deterministic wiki notes from processed news items."""

from __future__ import annotations

from ai_signal_radio.models import NewsItem, WikiNote


def note_from_item(item: NewsItem) -> WikiNote:
    topic = item.title.rstrip(".")
    summary = item.summary or f"{item.source} が「{topic}」について報じています。"
    interpretation = (
        f"この項目は {item.source_type} 系の情報で、"
        "モデル、開発ツール、研究動向、ローカルAI運用に影響する可能性があります。"
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
        tags=item.tags or ("ai",),
        fact_summary=summary,
        interpretation=interpretation,
        action_items=(
            "元情報を読み、具体的に何が変わったか確認する。",
            "このプロジェクトの監視リストを更新する必要があるか判断する。",
        ),
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
