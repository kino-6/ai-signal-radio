from datetime import datetime, timezone

import pytest

from ai_signal_radio.models import EditorialReview, NewsItem


def test_news_item_normalizes_and_serializes() -> None:
    item = NewsItem(
        source=" demo ",
        title="  New   AI   Tool ",
        url="https://example.com/story",
        summary=" summary ",
        published_at=datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc),
        tags=("AI", "ai", " Tools "),
    )

    assert item.source == "demo"
    assert item.source_type == "unknown"
    assert item.title == "New AI Tool"
    assert item.summary == "summary"
    assert item.tags == ("ai", "tools")
    assert item.id
    assert item.canonical_key
    assert item.content_hash
    assert item.collected_at.tzinfo is not None

    restored = NewsItem.from_dict(item.to_dict())
    assert restored == item
    assert restored.stable_id == item.stable_id


def test_news_item_requires_core_fields() -> None:
    with pytest.raises(ValueError):
        NewsItem(source="", title="Title", url="https://example.com")

    with pytest.raises(ValueError):
        NewsItem(source="source", title="", url="https://example.com")

    with pytest.raises(ValueError):
        NewsItem(source="source", title="Title", url="")


def test_wiki_note_serializes_radio_fields() -> None:
    note = NewsItem(
        source="demo",
        title="AI Radio Note",
        url="https://example.com/radio-note",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    from ai_signal_radio.processors.wiki_writer import note_from_item

    wiki_note = note_from_item(note)
    restored = type(wiki_note).from_dict(wiki_note.to_dict())

    assert restored.spoken_title
    assert restored.one_line_takeaway
    assert restored.why_it_matters
    assert restored.listen_action


def test_editorial_review_round_trips_and_clamps_score() -> None:
    review = EditorialReview.from_dict(
        {
            "relevance_score": 9,
            "read_in_daily": False,
            "wiki_only": True,
            "why_relevant": " プロセス改善に近い ",
            "process_improvement_angle": "レビュー工程の改善",
            "spoken_title": "AIレビュー改善",
            "one_line_takeaway": "AIでレビュー工程を短くできます。",
            "listen_action": "自分のレビュー工程を確認します。",
            "reject_reason": "",
        }
    )

    assert review.relevance_score == 5
    assert review.read_in_daily is False
    assert review.wiki_only is True
    assert review.why_relevant == "プロセス改善に近い"
    assert review.topic_angle == "レビュー工程の改善"
    assert review.to_dict()["spoken_title"] == "AIレビュー改善"
