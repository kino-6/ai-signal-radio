import json
from datetime import datetime, timezone

from ai_signal_radio.models import NewsItem
from ai_signal_radio.summarizers.ollama import OllamaSummarizer


def test_ollama_summarizer_uses_injected_transport() -> None:
    def fake_transport(request, timeout_seconds: int) -> bytes:
        assert request.full_url == "http://127.0.0.1:11434/api/generate"
        assert timeout_seconds == 120
        return json.dumps(
            {
                "response": json.dumps(
                    {
                        "fact_summary": "ローカルLLMで要約しました。",
                        "interpretation": "開発者が追うべき変化です。",
                        "action_items": ["元記事を確認する", "次回の実装候補に入れる"],
                        "spoken_title": "ローカルLLM要約の更新",
                        "one_line_takeaway": "ローカルLLMでニュース要約を作れます。",
                        "why_it_matters": "クラウドAPIなしで番組素材を作れるためです。",
                        "listen_action": "次に見るポイントは、要約品質です。",
                        "source_coverage": "単一ソースの情報です。",
                        "open_questions": ["公式発表はあるか"],
                    }
                )
            }
        ).encode("utf-8")

    summarizer = OllamaSummarizer(model="gemma4:latest", transport=fake_transport)
    item = NewsItem(
        source="demo",
        source_type="demo",
        title="AI agent update",
        url="https://example.com/agent",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        summary="A sample update.",
        tags=("ai",),
    )

    note = summarizer(item)

    assert note.fact_summary == "ローカルLLMで要約しました。"
    assert note.source == "demo"
    assert note.interpretation == "開発者が追うべき変化です。"
    assert note.action_items == ("元記事を確認する", "次回の実装候補に入れる")
    assert note.spoken_title == "ローカルLLM要約の更新"
    assert note.one_line_takeaway == "ローカルLLMでニュース要約を作れます。"
    assert note.why_it_matters == "クラウドAPIなしで番組素材を作れるためです。"
    assert note.listen_action == "次に見るポイントは、要約品質です。"
    assert note.source_coverage == "単一ソースの情報です。"
    assert note.open_questions == ("公式発表はあるか",)


def test_ollama_summarizer_falls_back_on_bad_response() -> None:
    def fake_transport(request, timeout_seconds: int) -> bytes:
        return b"not-json"

    summarizer = OllamaSummarizer(transport=fake_transport)
    item = NewsItem(
        source="demo",
        source_type="demo",
        title="AI agent update",
        url="https://example.com/agent",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        summary="A sample update.",
    )

    note = summarizer(item)

    assert note.fact_summary == "A sample update."


def test_ollama_summarizer_validates_empty_and_malformed_fields() -> None:
    def fake_transport(request, timeout_seconds: int) -> bytes:
        return json.dumps(
            {
                "response": json.dumps(
                    {
                        "fact_summary": "",
                        "interpretation": "x" * 500,
                        "action_items": "not-a-list",
                        "open_questions": [123, ""],
                    }
                )
            }
        ).encode("utf-8")

    summarizer = OllamaSummarizer(transport=fake_transport)
    item = NewsItem(
        source="demo",
        source_type="demo",
        title="AI agent update",
        url="https://example.com/agent",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        summary="Fallback fact.",
    )

    note = summarizer(item)

    assert note.fact_summary == "Fallback fact."
    assert len(note.interpretation) <= 320
    assert note.interpretation.endswith("…")
    assert note.action_items == (
        "元情報を読み、具体的に何が変わったか確認する。",
        "このプロジェクトの監視リストを更新する必要があるか判断する。",
    )
    assert note.one_line_takeaway == "demo が「AI agent update」について報じています。"
    assert note.why_it_matters
    assert note.listen_action
    assert note.open_questions == ("不明",)
