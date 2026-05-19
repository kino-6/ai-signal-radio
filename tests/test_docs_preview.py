from datetime import datetime, timezone

from ai_signal_radio.docs_preview import build_mkdocs_preview, find_latest_wiki_run
from ai_signal_radio.models import NewsItem
from ai_signal_radio.processors.wiki_writer import note_from_item, render_wiki_note, write_topic_pages
from ai_signal_radio.storage import save_processed_items


def test_build_mkdocs_preview_copies_latest_run_and_script(tmp_path) -> None:
    wiki_dir = tmp_path / "data" / "wiki"
    run_dir = wiki_dir / "2026-01-02" / "20260102T030405000000Z"
    run_dir.mkdir(parents=True)
    item = NewsItem(
        source="demo",
        source_type="demo",
        title="MkDocs AI Preview",
        url="https://example.com/mkdocs",
        published_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        score=5.0,
        tags=("ai",),
    )
    note = note_from_item(item)
    (run_dir / "01-mkdocs-ai-preview.md").write_text(render_wiki_note(note), encoding="utf-8")
    write_topic_pages([note], wiki_dir / "topics")

    script_path = tmp_path / "data" / "scripts" / "daily.md"
    script_path.parent.mkdir(parents=True)
    script_path.write_text("# Daily\n\n今日のAIニュースです。", encoding="utf-8")
    audio_dir = tmp_path / "data" / "audio"
    audio_dir.mkdir()
    (audio_dir / "daily.wav").write_bytes(b"RIFF daily")
    (audio_dir / "deep-dive.wav").write_bytes(b"RIFF deep")
    (audio_dir / "latest-metadata.json").write_text(
        '{"audio": {"daily": "data/audio/daily.wav"}}',
        encoding="utf-8",
    )
    processed_path = save_processed_items(
        [item],
        tmp_path / "data",
        run_id="20260102T030405000000Z",
        now=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    result = build_mkdocs_preview(
        wiki_dir=wiki_dir,
        script_path=script_path,
        audio_dir=audio_dir,
        output_dir=tmp_path / "docs" / "generated",
        processed_path=processed_path,
    )

    assert result.index_path.exists()
    assert result.radio_path and result.radio_path.exists()
    assert result.graph_path and result.graph_path.exists()
    assert result.copied_note_count == 1
    assert result.copied_topic_count == 1
    assert result.copied_audio_count == 1
    assert "MkDocs AI Preview" in result.index_path.read_text(encoding="utf-8")
    assert "Open graph view" in result.index_path.read_text(encoding="utf-8")
    assert "Daily audio" in result.index_path.read_text(encoding="utf-8")
    assert "audio/daily.wav" in result.index_path.read_text(encoding="utf-8")
    assert "AI Signal Graph" in result.graph_path.read_text(encoding="utf-8")
    assert "Daily Audio" in result.graph_path.read_text(encoding="utf-8")
    assert "<svg" in result.graph_path.read_text(encoding="utf-8")
    assert (
        tmp_path
        / "docs"
        / "generated"
        / "runs"
        / "2026-01-02"
        / "20260102T030405000000Z"
        / "01-mkdocs-ai-preview.md"
    ).exists()
    assert (tmp_path / "docs" / "generated" / "audio" / "daily.wav").exists()
    assert not (tmp_path / "docs" / "generated" / "audio" / "deep-dive.wav").exists()


def test_find_latest_wiki_run_prefers_latest_date_and_run(tmp_path) -> None:
    wiki_dir = tmp_path / "wiki"
    older = wiki_dir / "2026-01-01" / "run-a"
    latest = wiki_dir / "2026-01-02" / "run-b"
    older.mkdir(parents=True)
    latest.mkdir(parents=True)

    assert find_latest_wiki_run(wiki_dir) == latest
