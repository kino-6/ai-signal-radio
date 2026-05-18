from datetime import datetime, timezone

from ai_signal_radio import cli
from ai_signal_radio.models import NewsItem
from ai_signal_radio.processors.script_writer import render_script
from ai_signal_radio.processors.wiki_writer import note_from_item


def test_realistic_radio_pipeline_regression() -> None:
    published = datetime(2026, 5, 18, tzinfo=timezone.utc)
    items = [
        NewsItem(
            source="openai-official",
            source_type="rss",
            title="OpenAI releases new agent tools",
            url="https://openai.com/news/agent-tools",
            published_at=published,
            summary="OpenAIが新しいエージェント開発ツールを公開しました。",
            tags=("ai", "agent"),
        ),
        NewsItem(
            source="openai-official",
            source_type="rss",
            title="OpenAI releases new agent tools",
            url="https://openai.com/news/agent-tools?utm_source=newsletter&fbclid=abc",
            published_at=published,
            summary="OpenAIが新しいエージェント開発ツールを公開しました。",
            tags=("ai", "agent"),
        ),
        NewsItem(
            source="arxiv-ai",
            source_type="arxiv",
            title="Compact agent memory for long running AI tasks",
            url="https://arxiv.org/abs/2605.00001",
            published_at=published,
            content="A paper about memory systems for LLM agents.",
            tags=("ai", "llm"),
        ),
        NewsItem(
            source="hacker-news-ai",
            source_type="hackernews",
            title="Show HN: Sova AI mobile agent for Android apps",
            url="https://news.ycombinator.com/item?id=1",
            published_at=published,
            summary="Sova AIがAndroidアプリを操作するモバイルエージェントを公開しました。",
            content="Sova AI controls Android apps with accessibility APIs.",
            tags=("ai", "agent"),
            metadata={"points": 240},
        ),
        NewsItem(
            source="hacker-news-ai",
            source_type="hackernews",
            title="Google blocks Sova AI Android agent from Play Store",
            url="https://news.ycombinator.com/item?id=2",
            published_at=published,
            summary="Google Playの審査でSova AIのAndroidエージェントが止まりました。",
            content="Sova AI Android agent policy discussion.",
            tags=("ai", "policy"),
            metadata={"points": 180},
        ),
        NewsItem(
            source="hacker-news-ai",
            source_type="hackernews",
            title="OpenHarness ships",
            url="https://news.ycombinator.com/item?id=3",
            published_at=published,
            summary="OpenHarness ships.",
            content="Terminal coding agent for any LLM.",
            tags=("llm", "coding"),
            metadata={"points": 120},
        ),
        NewsItem(
            source="vendor-blog",
            source_type="rss",
            title="Local LLM observability with SQLite",
            url="https://example.com/sqlite-llm-observability?gclid=1&ref=twitter",
            published_at=published,
            tags=("llm", "local-first"),
        ),
    ]

    dedupe_result, ranked, processed = cli._process_items(items, limit=8)
    notes = [note_from_item(item) for item in processed]
    script = render_script(notes, style="briefing")

    assert processed
    assert all("score_breakdown" in item.metadata for item in processed)
    assert dedupe_result.duplicate_groups
    assert dedupe_result.duplicate_groups[0].reason == "same_canonical_url"
    assert len(processed) == len(ranked) == dedupe_result.output_count
    assert all("topic_cluster" in item.metadata for item in processed)
    assert any(item.metadata["topic_cluster"]["size"] > 1 for item in processed)
    assert any("について報じています" in note.fact_summary for note in notes)
    assert any("ローカルAI運用に影響する可能性があります" in note.interpretation for note in notes)
    assert script.count("OpenHarness ships") == 1
