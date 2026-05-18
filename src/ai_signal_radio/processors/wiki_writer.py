"""Markdown wiki note generation."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

from ai_signal_radio.models import NewsItem, WikiNote
from ai_signal_radio.storage import date_slug

Summarizer = Callable[[NewsItem], WikiNote]


def write_wiki_notes(
    items: list[NewsItem],
    output_dir: Path,
    now: datetime | None = None,
    summarizer: Summarizer | None = None,
    clean_day: bool = False,
) -> list[Path]:
    """Write one Markdown wiki note per news item.

    The optional summarizer is the future LLM extension point. The MVP uses
    deterministic placeholders so tests and demo runs never need API keys.
    """

    generated = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    day_dir = output_dir / date_slug(generated)
    day_dir.mkdir(parents=True, exist_ok=True)
    if clean_day:
        for path in day_dir.glob("*.md"):
            path.unlink()

    paths: list[Path] = []
    for index, item in enumerate(items, start=1):
        note = summarizer(item) if summarizer else note_from_item(item)
        path = day_dir / f"{index:02d}-{_slugify(note.title)}.md"
        path.write_text(render_wiki_note(note), encoding="utf-8")
        paths.append(path)
    return paths


def note_from_item(item: NewsItem) -> WikiNote:
    topic = item.title.rstrip(".")
    summary = item.summary or f"{item.source} reported: {topic}."
    interpretation = (
        f"This item may matter for AI builders because it touches {item.source_type} "
        "signals that can affect models, tools, research, or local workflows."
    )
    return WikiNote(
        title=item.title,
        source=item.source,
        source_url=item.url,
        source_type=item.source_type,
        published_at=item.published_at,
        collected_at=item.collected_at,
        tags=item.tags or ("ai",),
        fact_summary=summary,
        interpretation=interpretation,
        action_items=(
            "Read the source and confirm the concrete change.",
            "Decide whether this should update the project watch list.",
        ),
        score=item.score,
    )


def render_wiki_note(note: WikiNote) -> str:
    frontmatter = yaml.safe_dump(
        {
            "title": note.title,
            "source": note.source,
            "source_url": note.source_url,
            "source_type": note.source_type,
            "published_at": note.published_at.isoformat(),
            "collected_at": note.collected_at.isoformat(),
            "tags": list(note.tags),
            "score": note.score,
        },
        sort_keys=False,
        allow_unicode=True,
    ).strip()

    action_items = "\n".join(f"- {item}" for item in note.action_items)
    return (
        f"---\n{frontmatter}\n---\n\n"
        f"# {note.title}\n\n"
        "## Fact Summary\n\n"
        f"{note.fact_summary}\n\n"
        "## Interpretation\n\n"
        f"{note.interpretation}\n\n"
        "## Action Items\n\n"
        f"{action_items}\n\n"
        "## Source\n\n"
        f"- Source: {note.source}\n"
        f"- Type: {note.source_type}\n"
        f"- URL: {note.source_url}\n"
    )


def load_wiki_notes(input_path: Path) -> list[WikiNote]:
    paths = _markdown_paths(input_path)
    notes: list[WikiNote] = []
    for path in paths:
        try:
            notes.append(parse_wiki_note(path.read_text(encoding="utf-8")))
        except (KeyError, TypeError, ValueError):
            continue
    return notes


def parse_wiki_note(markdown: str) -> WikiNote:
    metadata, body = _split_frontmatter(markdown)
    sections = _parse_sections(body)
    action_items = tuple(
        line.removeprefix("- ").strip()
        for line in sections.get("Action Items", "").splitlines()
        if line.strip().startswith("- ")
    )
    return WikiNote.from_dict(
        {
            **metadata,
            "fact_summary": sections.get("Fact Summary", "").strip(),
            "interpretation": sections.get("Interpretation", "").strip(),
            "action_items": action_items,
        }
    )


def _markdown_paths(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if not input_path.exists():
        return []
    dated_dirs = sorted(
        path
        for path in input_path.iterdir()
        if path.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.name)
    )
    if dated_dirs:
        latest_dir = dated_dirs[-1]
        return sorted(path for path in latest_dir.glob("*.md") if path.is_file())
    return sorted(path for path in input_path.rglob("*.md") if path.is_file())


def _split_frontmatter(markdown: str) -> tuple[dict, str]:
    if not markdown.startswith("---\n"):
        raise ValueError("wiki note is missing frontmatter")
    _, raw_metadata, body = markdown.split("---", 2)
    return yaml.safe_load(raw_metadata) or {}, body


def _parse_sections(body: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in body.splitlines():
        if line.startswith("## "):
            current = line.removeprefix("## ").strip()
            sections[current] = []
        elif current:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "note"


def write_wiki(items: list[NewsItem], output_dir: Path, now: datetime | None = None) -> Path:
    """Backward-compatible wrapper returning the written day directory."""

    paths = write_wiki_notes(items, output_dir, now)
    return paths[0].parent if paths else output_dir / date_slug(now)
