from datetime import datetime, timezone

from ai_signal_radio.models import WikiNote
from ai_signal_radio.processors.script_writer import render_script


def test_render_script_is_japanese_tts_friendly() -> None:
    note = WikiNote(
        title="LLM agent update",
        source="example-rss",
        source_url="https://example.com",
        source_type="rss",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("ai",),
        fact_summary="新しいエージェント機能が公開されました。",
        interpretation="開発者のワークフローに影響する可能性があります。",
        action_items=("元記事を確認する",),
        score=5.0,
    )

    script = render_script([note])

    assert script.startswith("# Daily AI Signal Radio")
    assert "こんにちは。今日のAIニュースです。" in script
    assert "今日の注目トピックは 1 件です。" in script
    assert "取得元は example-rss です。" in script
    assert "それでは、今日もよい開発を。" in script
