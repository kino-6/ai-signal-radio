import json
from datetime import datetime, timezone

from ai_signal_radio.config import EditorialSkill, TopicProfile
from ai_signal_radio.editorial import OllamaEditorialReviewer, fallback_editorial_review
from ai_signal_radio.models import NewsItem


def _item() -> NewsItem:
    return NewsItem(
        source="demo",
        source_type="hackernews",
        title="AI workflow automation for code reviews",
        url="https://example.com/workflow",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        summary="AIでコードレビュー工程を短くする事例です。",
        score=8,
        tags=("ai", "workflow"),
        metadata={
            "score_breakdown": {"total": 8, "keyword_matches": ["workflow"]},
            "topic_cluster": {"id": "workflow", "label": "workflow", "size": 1},
        },
    )


def test_ollama_editorial_reviewer_uses_injected_transport() -> None:
    skill = EditorialSkill(
        name="process",
        audience="業務改善担当者",
        purpose="AIでプロセス改善に効くニュースを選ぶ",
        accept=("レビュー工程の改善",),
        reject=("モデル性能だけ",),
        framing="小さく試せる観点を言う",
    )
    seen: dict[str, object] = {}

    def fake_transport(request, timeout_seconds: int) -> bytes:
        seen["url"] = request.full_url
        seen["timeout"] = timeout_seconds
        body = json.loads(request.data.decode("utf-8"))
        seen["prompt"] = body["prompt"]
        return json.dumps(
            {
                "response": json.dumps(
                    {
                        "relevance_score": 5,
                        "read_in_daily": True,
                        "wiki_only": False,
                        "why_relevant": "レビュー工程の短縮に直結するためです。",
                        "topic_angle": "コードレビューのプロセス改善",
                        "spoken_title": "AIによるレビュー工程の短縮",
                        "one_line_takeaway": "AIでレビュー待ち時間を減らせる可能性があります。",
                        "listen_action": "自分のレビュー待ち時間を確認します。",
                        "reject_reason": "",
                    }
                )
            }
        ).encode("utf-8")

    reviewer = OllamaEditorialReviewer(
        skill=skill,
        model="gemma4:latest",
        transport=fake_transport,
        topic_profile=TopicProfile(name="process"),
    )

    review = reviewer(_item())

    assert seen["url"] == "http://127.0.0.1:11434/api/generate"
    assert seen["timeout"] == 120
    assert "AI workflow automation" in str(seen["prompt"])
    assert "レビュー工程の改善" in str(seen["prompt"])
    assert review.relevance_score == 5
    assert review.read_in_daily is True
    assert review.wiki_only is False
    assert review.spoken_title == "AIによるレビュー工程の短縮"
    assert review.one_line_takeaway == "AIでレビュー待ち時間を減らせる可能性があります。"


def test_ollama_editorial_reviewer_falls_back_on_bad_response() -> None:
    def fake_transport(request, timeout_seconds: int) -> bytes:
        return b"not-json"

    skill = EditorialSkill(name="process", relevance_threshold=3)
    reviewer = OllamaEditorialReviewer(skill=skill, transport=fake_transport)

    review = reviewer(_item())

    assert review == fallback_editorial_review(_item(), skill)
    assert review.read_in_daily is True


def test_ollama_editorial_reviewer_marks_wiki_only_when_model_rejects() -> None:
    def fake_transport(request, timeout_seconds: int) -> bytes:
        return json.dumps(
            {
                "response": json.dumps(
                    {
                        "relevance_score": 2,
                        "read_in_daily": False,
                        "wiki_only": True,
                        "reject_reason": "モデル性能だけの話に近いため。",
                    }
                )
            }
        ).encode("utf-8")

    reviewer = OllamaEditorialReviewer(
        skill=EditorialSkill(name="process", relevance_threshold=3),
        transport=fake_transport,
    )

    review = reviewer(_item())

    assert review.relevance_score == 2
    assert review.read_in_daily is False
    assert review.wiki_only is True
    assert review.reject_reason == "モデル性能だけの話に近いため。"
