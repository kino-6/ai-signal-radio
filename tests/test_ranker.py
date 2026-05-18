from datetime import datetime, timezone

from ai_signal_radio.models import NewsItem
from ai_signal_radio.processors.ranker import rank_items, score_item


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
