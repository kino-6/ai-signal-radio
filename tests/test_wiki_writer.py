from datetime import datetime, timezone

from ai_signal_radio.models import NewsItem
from ai_signal_radio.processors.wiki_writer import render_wiki, write_wiki


def test_render_wiki_contains_llm_friendly_sections() -> None:
    item = NewsItem(
        source="demo",
        title="Local AI Briefing Tool Ships",
        url="https://example.com/local-ai-briefing",
        summary="A local-first pipeline writes Markdown notes for later LLM use.",
        published_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        tags=("local-first",),
    )

    markdown = render_wiki([item], datetime(2026, 1, 3, tzinfo=timezone.utc))

    assert "# AI Signal Radio - 2026-01-03" in markdown
    assert "## Signals" in markdown
    assert "### 1. Local AI Briefing Tool Ships" in markdown
    assert "#### LLM Notes" in markdown
    assert "https://example.com/local-ai-briefing" in markdown


def test_write_wiki_creates_markdown_file(tmp_path) -> None:
    path = write_wiki([], tmp_path, datetime(2026, 1, 3, tzinfo=timezone.utc))

    assert path.name == "2026-01-03-ai-signal-radio.md"
    assert "No items collected." in path.read_text(encoding="utf-8")
