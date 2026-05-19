from datetime import datetime, timezone

from ai_signal_radio.config import RankerConfig, TopicProfile
from ai_signal_radio.models import NewsItem
from ai_signal_radio.processors.ranker import rank_items, score_breakdown, score_item


def test_score_item_is_transparent_heuristic() -> None:
    item = NewsItem(
        source="OpenAI Blog",
        source_type="rss",
        title="OpenAI releases new agent model",
        url="https://openai.com/example",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("ai",),
    )

    assert score_item(item) >= 8.0


def test_rank_items_writes_score() -> None:
    item = NewsItem(
        source="arXiv",
        source_type="arxiv",
        title="LLM benchmark paper",
        url="https://arxiv.org/abs/1234.5678",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    ranked = rank_items([item])

    assert ranked[0].score > 0
    assert ranked[0].metadata["score_breakdown"]["total"] == ranked[0].score


def test_score_breakdown_explains_total() -> None:
    item = NewsItem(
        source="Hacker News",
        source_type="hackernews",
        title="LLM agent discussion",
        url="https://news.ycombinator.com/item?id=1",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        metadata={"points": 120},
    )

    breakdown = score_breakdown(item)

    assert "llm" in breakdown["keyword_matches"]
    assert "agent" in breakdown["keyword_matches"]
    assert breakdown["keyword_score"] > 0
    assert breakdown["hn_points_bonus"] == 1.2
    assert breakdown["total"] == score_item(item)


def test_score_item_uses_configurable_weights() -> None:
    item = NewsItem(
        source="OpenAI Blog",
        source_type="rss",
        title="OpenAI releases new agent model",
        url="https://openai.com/example",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    config = RankerConfig(keyword_bonus=1.0, official_source_bonus=10.0)

    assert score_item(item, config=config) >= 13.0


def test_score_item_uses_topic_profile_keywords_and_sources() -> None:
    item = NewsItem(
        source="CISA",
        source_type="rss",
        title="CVE exploit advisory",
        url="https://cisa.gov/example",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    profile = TopicProfile(
        name="security",
        score_keywords=("cve", "exploit"),
        official_sources=("cisa",),
    )

    breakdown = score_breakdown(item, topic_profile=profile)

    assert breakdown["topic_profile"] == "security"
    assert breakdown["keyword_matches"] == ["cve", "exploit"]
    assert breakdown["official_source_bonus"] > 0


def test_rank_items_keeps_source_diversity() -> None:
    published = datetime(2026, 1, 1, tzinfo=timezone.utc)
    items = [
        NewsItem(
            source="hacker-news-ai",
            source_type="hackernews",
            title=f"OpenAI agent model discussion {index}",
            url=f"https://news.ycombinator.com/item?id={index}",
            published_at=published,
            metadata={"points": 500},
        )
        for index in range(5)
    ]
    items.extend(
        [
            NewsItem(
                source="arxiv-ai",
                source_type="arxiv",
                title="LLM benchmark research",
                url="https://arxiv.org/abs/1234.0001",
                published_at=published,
            ),
            NewsItem(
                source="arxiv-ai",
                source_type="arxiv",
                title="Agent memory research",
                url="https://arxiv.org/abs/1234.0002",
                published_at=published,
            ),
        ]
    )

    ranked = rank_items(items, limit=4)

    assert len(ranked) == 4
    assert sum(item.source_type == "hackernews" for item in ranked) <= 3
    assert any(item.source_type == "arxiv" for item in ranked)


def test_rank_items_fills_with_hackernews_when_no_other_sources_exist() -> None:
    published = datetime(2026, 1, 1, tzinfo=timezone.utc)
    items = [
        NewsItem(
            source="hacker-news-ai",
            source_type="hackernews",
            title=f"AI agent model discussion {index}",
            url=f"https://news.ycombinator.com/item?id={index}",
            published_at=published,
            metadata={"points": 100},
        )
        for index in range(5)
    ]

    ranked = rank_items(items, limit=4)

    assert len(ranked) == 4


def test_rank_items_uses_configurable_source_limits() -> None:
    published = datetime(2026, 1, 1, tzinfo=timezone.utc)
    hn_items = [
        NewsItem(
            source="hacker-news-ai",
            source_type="hackernews",
            title=f"AI agent model discussion {index}",
            url=f"https://news.ycombinator.com/item?id={index}",
            published_at=published,
            metadata={"points": 500},
        )
        for index in range(4)
    ]
    rss_item = NewsItem(
        source="OpenAI Blog",
        source_type="rss",
        title="OpenAI model release",
        url="https://openai.com/example",
        published_at=published,
    )
    config = RankerConfig(
        min_source_types={"rss": 1},
        max_source_types={"hackernews": 1},
    )

    ranked = rank_items([*hn_items, rss_item], limit=3, config=config)

    assert sum(item.source_type == "hackernews" for item in ranked) <= 1
    assert any(item.source_type == "rss" for item in ranked)


def test_rank_items_prefers_distant_topic_clusters_for_daily_selection() -> None:
    published = datetime(2026, 1, 1, tzinfo=timezone.utc)
    sova_items = [
        NewsItem(
            source="hacker-news-ai",
            source_type="hackernews",
            title=f"Sova AI Android agent follow-up {index}",
            url=f"https://news.ycombinator.com/item?id=sova-{index}",
            published_at=published,
            tags=("ai", "agent"),
            metadata={"points": 500 - index},
        )
        for index in range(3)
    ]
    other_items = [
        NewsItem(
            source="hacker-news-ai",
            source_type="hackernews",
            title="OpenHarness terminal coding agent ships",
            url="https://news.ycombinator.com/item?id=open-harness",
            published_at=published,
            tags=("llm", "coding"),
            metadata={"points": 120},
        ),
        NewsItem(
            source="hacker-news-ai",
            source_type="hackernews",
            title="Local LLM observability with SQLite",
            url="https://news.ycombinator.com/item?id=sqlite",
            published_at=published,
            tags=("llm", "local-first"),
            metadata={"points": 80},
        ),
    ]

    ranked = rank_items([*sova_items, *other_items], limit=3)

    cluster_ids = [
        item.metadata["topic_cluster"]["id"]
        for item in ranked
        if isinstance(item.metadata.get("topic_cluster"), dict)
    ]
    assert len(ranked) == 3
    assert len(set(cluster_ids)) == 3
    assert sum("Sova AI" in item.title for item in ranked) == 1


def test_rank_items_can_allow_multiple_items_from_same_topic_cluster() -> None:
    published = datetime(2026, 1, 1, tzinfo=timezone.utc)
    items = [
        NewsItem(
            source="hacker-news-ai",
            source_type="hackernews",
            title=f"Sova AI Android agent follow-up {index}",
            url=f"https://news.ycombinator.com/item?id=sova-{index}",
            published_at=published,
            tags=("ai", "agent"),
            metadata={"points": 500 - index},
        )
        for index in range(3)
    ]
    items.append(
        NewsItem(
            source="hacker-news-ai",
            source_type="hackernews",
            title="OpenHarness terminal coding agent ships",
            url="https://news.ycombinator.com/item?id=open-harness",
            published_at=published,
            tags=("llm", "coding"),
            metadata={"points": 120},
        )
    )

    ranked = rank_items(items, limit=3, config=RankerConfig(max_topic_cluster_items=2))

    assert sum("Sova AI" in item.title for item in ranked) == 2
