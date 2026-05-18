from datetime import datetime, timezone

from ai_signal_radio.models import NewsItem
from ai_signal_radio.storage import (
    load_raw_items,
    save_processed_items,
    save_run_metadata,
    timestamp_slug,
)


def test_timestamp_slug_includes_subsecond_run_id() -> None:
    value = datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc)

    assert timestamp_slug(value) == "20260102T030405123456Z"


def test_save_processed_items_writes_latest_and_archive(tmp_path) -> None:
    item = NewsItem(
        source="demo",
        source_type="demo",
        title="Processed AI item",
        url="https://example.com/processed",
        published_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    latest = save_processed_items(
        [item],
        tmp_path,
        run_id="20260102T030405123456Z",
        now=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    archive = tmp_path / "processed" / "2026-01-02" / "20260102T030405123456Z.json"
    assert latest == tmp_path / "processed" / "latest.json"
    assert archive.exists()
    assert load_raw_items(latest)[0].title == "Processed AI item"


def test_save_run_metadata_writes_latest_and_archive(tmp_path) -> None:
    latest = save_run_metadata(
        {"run_id": "20260102T030405123456Z", "source_coverage": {"selected": {"total": 0}}},
        tmp_path,
        run_id="20260102T030405123456Z",
        now=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    archive = tmp_path / "processed" / "2026-01-02" / "20260102T030405123456Z-metadata.json"
    assert latest == tmp_path / "processed" / "latest-metadata.json"
    assert archive.exists()
    assert '"run_id": "20260102T030405123456Z"' in latest.read_text(encoding="utf-8")
