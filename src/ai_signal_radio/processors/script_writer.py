"""Radio-style script generation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ai_signal_radio.models import NewsItem
from ai_signal_radio.storage import date_slug


def write_script(items: list[NewsItem], output_dir: Path, now: datetime | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{date_slug(now)}-radio-script.md"
    path.write_text(render_script(items, now), encoding="utf-8")
    return path


def render_script(items: list[NewsItem], now: datetime | None = None) -> str:
    generated = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    lines = [
        f"# AI Signal Radio Script - {generated:%Y-%m-%d}",
        "",
        "Good day. This is AI Signal Radio, with a short local-first briefing.",
        "",
    ]

    if not items:
        lines.extend(
            [
                "No fresh items were collected for this run.",
                "",
                "That is the signal for now.",
                "",
            ]
        )
        return "\n".join(lines)

    for item in items:
        summary = item.summary or "Details are still sparse, but the item is worth tracking."
        lines.extend(
            [
                f"Next: {item.title}.",
                summary,
                "",
            ]
        )

    lines.extend(
        [
            "That is the signal for now. Archive the notes, keep the context, and stay tuned.",
            "",
        ]
    )
    return "\n".join(lines)
