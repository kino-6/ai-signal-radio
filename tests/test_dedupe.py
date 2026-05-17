from datetime import datetime, timezone

from ai_signal_radio.models import NewsItem
from ai_signal_radio.processors.dedupe import canonical_url, dedupe_items, normalize_title


def test_canonical_url_removes_tracking_and_fragments() -> None:
    url = "HTTPS://Example.COM/story/?utm_source=x&keep=1#section"

    assert canonical_url(url) == "https://example.com/story?keep=1"


def test_normalize_title_compacts_punctuation_and_case() -> None:
    assert normalize_title("New AI Tool:  Really?") == "new ai tool really"


def test_dedupe_items_prefers_richer_duplicate() -> None:
    published = datetime(2026, 1, 1, tzinfo=timezone.utc)
    sparse = NewsItem(
        source="rss",
        title="New AI Tool",
        url="https://example.com/story?utm_source=newsletter",
        summary="Short.",
        published_at=published,
    )
    rich = NewsItem(
        source="hn",
        title="New AI Tool",
        url="https://example.com/story",
        summary="A longer summary with more useful context.",
        published_at=published,
        tags=("discussion",),
    )

    result = dedupe_items([sparse, rich])

    assert result == [rich]
