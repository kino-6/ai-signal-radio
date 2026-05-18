from datetime import datetime, timezone

from ai_signal_radio.models import NewsItem
from ai_signal_radio.processors.topic_cluster import cluster_items


def item(title: str, content: str = "") -> NewsItem:
    return NewsItem(
        source="hn",
        source_type="hackernews",
        title=title,
        url=f"https://example.com/{abs(hash(title))}",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        content=content,
    )


def test_cluster_items_groups_same_product_topic() -> None:
    first = item(
        "Google banned our mobile AI agent app",
        "We built Sova AI, an Android assistant using the Accessibility API.",
    )
    second = item(
        "Show HN: Android AI agent-assistant operating your apps",
        "Sova AI controls Android apps without adb or root.",
    )
    unrelated = item("Show HN: OpenHarness Open-source terminal coding agent")

    clustered = cluster_items([first, second, unrelated])

    first_cluster = clustered[0].metadata["topic_cluster"]
    second_cluster = clustered[1].metadata["topic_cluster"]
    unrelated_cluster = clustered[2].metadata["topic_cluster"]
    assert first_cluster["id"] == second_cluster["id"]
    assert first_cluster["size"] == 2
    assert first_cluster["is_representative"] is True
    assert second_cluster["is_representative"] is False
    assert first_cluster["related_titles"] == [second.title]
    assert unrelated_cluster["size"] == 1
