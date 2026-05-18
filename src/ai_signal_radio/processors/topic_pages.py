"""Markdown topic index page generation."""

from __future__ import annotations

import re
from pathlib import Path

from ai_signal_radio.models import WikiNote


def write_topic_pages(notes: list[WikiNote], output_dir: Path) -> list[Path]:
    """Write lightweight topic index pages grouped by tag."""

    output_dir.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[WikiNote]] = {}
    for note in notes:
        for tag in note.tags or ("ai",):
            grouped.setdefault(tag, []).append(note)

    paths: list[Path] = []
    for tag, topic_notes in sorted(grouped.items()):
        path = output_dir / f"{slugify(tag)}.md"
        path.write_text(render_topic_page(tag, topic_notes), encoding="utf-8")
        paths.append(path)
    return paths


def render_topic_page(tag: str, notes: list[WikiNote]) -> str:
    lines = [
        f"# Topic: {tag}",
        "",
        f"関連ノート: {len(notes)} 件",
        "",
    ]
    for note in sorted(notes, key=lambda item: item.published_at, reverse=True):
        lines.extend(
            [
                f"## {note.title}",
                "",
                f"- Source: {note.source}",
                f"- URL: {note.source_url}",
                f"- Score: {note.score}",
                "",
                note.fact_summary,
                "",
            ]
        )
    return "\n".join(lines)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "note"
