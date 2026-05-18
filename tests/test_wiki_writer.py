from datetime import datetime, timezone

from ai_signal_radio.models import NewsItem
from ai_signal_radio.processors.wiki_writer import (
    load_wiki_notes,
    note_from_item,
    render_wiki_note,
    write_wiki_notes,
)


def test_render_wiki_note_contains_frontmatter_and_sections() -> None:
    item = NewsItem(
        source="demo",
        source_type="demo",
        title="Local AI Briefing Tool Ships",
        url="https://example.com/local-ai-briefing",
        summary="A local-first pipeline writes Markdown notes for later LLM use.",
        published_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
        tags=("local-first", "llm"),
        score=4.0,
    )

    markdown = render_wiki_note(note_from_item(item))

    assert markdown.startswith("---\n")
    assert 'title: Local AI Briefing Tool Ships' in markdown
    assert "source: demo" in markdown
    assert "source_url: https://example.com/local-ai-briefing" in markdown
    assert "## Fact Summary" in markdown
    assert "## Interpretation" in markdown
    assert "## Action Items" in markdown
    assert "## Source" in markdown


def test_write_wiki_notes_creates_daily_markdown_files(tmp_path) -> None:
    item = NewsItem(
        source="demo",
        source_type="demo",
        title="Local AI Briefing Tool Ships",
        url="https://example.com/local-ai-briefing",
        summary="A local-first pipeline writes Markdown notes for later LLM use.",
        published_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
        tags=("local-first",),
    )

    paths = write_wiki_notes([item], tmp_path, datetime(2026, 1, 3, tzinfo=timezone.utc))
    notes = load_wiki_notes(tmp_path)

    assert len(paths) == 1
    assert paths[0].parent.name == "2026-01-03"
    assert paths[0].suffix == ".md"
    assert notes[0].title == "Local AI Briefing Tool Ships"
    assert notes[0].source == "demo"


def test_write_wiki_notes_can_clean_stale_daily_files(tmp_path) -> None:
    stale_dir = tmp_path / "2026-01-03"
    stale_dir.mkdir()
    stale = stale_dir / "old.md"
    stale.write_text("old", encoding="utf-8")
    item = NewsItem(
        source="demo",
        source_type="demo",
        title="Fresh AI Briefing",
        url="https://example.com/fresh-ai-briefing",
        published_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
    )

    paths = write_wiki_notes(
        [item],
        tmp_path,
        datetime(2026, 1, 3, tzinfo=timezone.utc),
        clean_day=True,
    )

    assert not stale.exists()
    assert len(paths) == 1
