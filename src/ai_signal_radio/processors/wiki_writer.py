"""Markdown wiki note generation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ai_signal_radio.models import NewsItem
from ai_signal_radio.storage import date_slug


def write_wiki(items: list[NewsItem], output_dir: Path, now: datetime | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{date_slug(now)}-ai-signal-radio.md"
    path.write_text(render_wiki(items, now), encoding="utf-8")
    return path


def render_wiki(items: list[NewsItem], now: datetime | None = None) -> str:
    generated = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    lines = [
        f"# AI Signal Radio - {generated:%Y-%m-%d}",
        "",
        f"Generated: {generated.isoformat()}",
        "",
        "## Summary",
        "",
        f"- Items reviewed: {len(items)}",
        "- Focus: AI systems, tooling, research, local-first workflows, and developer impact.",
        "",
        "## Signals",
        "",
    ]

    if not items:
        lines.extend(["No items collected.", ""])
        return "\n".join(lines)

    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                f"### {index}. {item.title}",
                "",
                f"- Source: {item.source}",
                f"- Published: {item.published_at.isoformat()}",
                f"- URL: {item.url}",
                f"- Tags: {', '.join(item.tags) if item.tags else 'unlabeled'}",
                "",
                item.summary or "No summary provided.",
                "",
                "#### LLM Notes",
                "",
                "- Why it matters: Capture relevance for AI builders and local-first workflows.",
                "- Follow-up questions: What changed, who is affected, and what should be tracked next?",
                "",
            ]
        )

    return "\n".join(lines)
