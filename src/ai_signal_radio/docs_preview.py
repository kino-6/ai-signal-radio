"""MkDocs preview generation for local wiki outputs."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from html import escape
from pathlib import Path

from ai_signal_radio.models import NewsItem, WikiNote
from ai_signal_radio.processors.wiki_writer import load_wiki_notes
from ai_signal_radio.storage import load_raw_items


@dataclass(frozen=True)
class DocsPreviewResult:
    output_dir: Path
    index_path: Path
    copied_note_count: int
    copied_topic_count: int
    radio_path: Path | None
    graph_path: Path | None = None


def build_mkdocs_preview(
    wiki_dir: Path = Path("data/wiki"),
    script_path: Path = Path("data/scripts/daily.md"),
    output_dir: Path = Path("docs/generated"),
    processed_path: Path | None = Path("data/processed/latest.json"),
) -> DocsPreviewResult:
    """Create ignored Markdown files that MkDocs can render locally."""

    latest_run_dir = find_latest_wiki_run(wiki_dir)
    _reset_dir(output_dir)

    copied_notes: list[Path] = []
    notes: list[WikiNote] = []
    if latest_run_dir:
        relative_run_dir = _preview_run_dir(latest_run_dir, wiki_dir)
        destination = output_dir / "runs" / relative_run_dir
        destination.mkdir(parents=True, exist_ok=True)
        copied_notes = _copy_markdown_files(latest_run_dir, destination)
        notes = load_wiki_notes(latest_run_dir)

    topic_source_dir = wiki_dir / "topics"
    copied_topics: list[Path] = []
    if topic_source_dir.exists():
        topic_destination = output_dir / "topics"
        topic_destination.mkdir(parents=True, exist_ok=True)
        copied_topics = _copy_markdown_files(topic_source_dir, topic_destination)

    radio_path = None
    if script_path.exists():
        radio_path = output_dir / "radio.md"
        shutil.copyfile(script_path, radio_path)

    processed_items = _load_processed_items(processed_path)
    graph_path = output_dir / "graph.md"
    graph_path.write_text(
        render_graph_page(
            notes=notes,
            note_paths=copied_notes,
            topic_paths=copied_topics,
            radio_path=radio_path,
            output_dir=output_dir,
        ),
        encoding="utf-8",
    )
    index_path = output_dir / "daily.md"
    index_path.write_text(
        render_preview_index(
            notes=notes,
            note_paths=copied_notes,
            topic_paths=copied_topics,
            radio_path=radio_path,
            processed_items=processed_items,
            latest_run_dir=latest_run_dir,
            output_dir=output_dir,
            graph_path=graph_path,
        ),
        encoding="utf-8",
    )
    return DocsPreviewResult(
        output_dir=output_dir,
        index_path=index_path,
        copied_note_count=len(copied_notes),
        copied_topic_count=len(copied_topics),
        radio_path=radio_path,
        graph_path=graph_path,
    )


def render_preview_index(
    notes: list[WikiNote],
    note_paths: list[Path],
    topic_paths: list[Path],
    radio_path: Path | None,
    processed_items: list[NewsItem],
    latest_run_dir: Path | None,
    output_dir: Path,
    graph_path: Path | None = None,
) -> str:
    lines = [
        "# Daily AI Signal Preview",
        "",
        "MkDocs で読むためのローカル生成プレビューです。",
        "",
    ]
    if latest_run_dir:
        lines.extend(["## Latest Wiki Run", "", f"`{latest_run_dir}`", ""])

    if graph_path:
        relative_graph = graph_path.relative_to(output_dir).as_posix()
        lines.extend(["## Graph View", "", f"- [Open graph view]({relative_graph})", ""])

    lines.extend(["## Notes", ""])
    if notes and note_paths:
        for index, (note, path) in enumerate(zip(notes, note_paths, strict=False), start=1):
            relative = path.relative_to(output_dir).as_posix()
            lines.append(f"{index}. [{note.title}]({relative}) - {note.source} / score {note.score}")
        lines.append("")
    else:
        lines.extend(["まだ表示できる wiki note がありません。", ""])

    if radio_path:
        relative_radio = radio_path.relative_to(output_dir).as_posix()
        lines.extend(["## Radio Script", "", f"- [Daily script]({relative_radio})", ""])

    lines.extend(["## Topics", ""])
    if topic_paths:
        for path in topic_paths:
            relative = path.relative_to(output_dir).as_posix()
            lines.append(f"- [{path.stem}]({relative})")
        lines.append("")
    else:
        lines.extend(["まだ topic page がありません。", ""])

    if processed_items:
        lines.extend(["## Score Snapshot", "", "| Title | Source | Score |", "| --- | --- | --- |"])
        for item in processed_items:
            lines.append(f"| {_escape_table(item.title)} | {_escape_table(item.source)} | {item.score} |")
        lines.append("")

    return "\n".join(lines)


def render_graph_page(
    notes: list[WikiNote],
    note_paths: list[Path],
    topic_paths: list[Path],
    radio_path: Path | None,
    output_dir: Path,
) -> str:
    return "\n".join(
        [
            "# AI Signal Graph",
            "",
            "ニュース、topic、radio script の関係をざっくり見るためのローカルグラフです。",
            "",
            render_signal_graph(
                notes=notes,
                note_paths=note_paths,
                topic_paths=topic_paths,
                radio_path=radio_path,
                output_dir=output_dir,
            ),
            "",
        ]
    )


def render_signal_graph(
    notes: list[WikiNote],
    note_paths: list[Path],
    topic_paths: list[Path],
    radio_path: Path | None,
    output_dir: Path,
) -> str:
    width = 1100
    topic_tags = sorted({tag for note in notes for tag in note.tags} | {path.stem for path in topic_paths})
    height = max(520, 170 + 92 * max(len(notes), len(topic_tags), 1))

    topic_y = _column_positions(len(topic_tags), height)
    note_y = _column_positions(len(notes), height)
    radio_y = height // 2

    topic_links = {
        path.stem: path.relative_to(output_dir).as_posix()
        for path in topic_paths
    }
    note_links = [
        path.relative_to(output_dir).as_posix()
        for path in note_paths
    ]
    radio_link = radio_path.relative_to(output_dir).as_posix() if radio_path else None

    topic_index = {tag: index for index, tag in enumerate(topic_tags)}

    lines = [
        '<div class="ai-signal-graph">',
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        'aria-label="AI Signal news graph" xmlns="http://www.w3.org/2000/svg">',
        "<defs>",
        '<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" '
        'orient="auto" markerUnits="strokeWidth">',
        '<path d="M0,0 L0,6 L9,3 z" fill="#78909c" />',
        "</marker>",
        "</defs>",
        '<style><![CDATA[',
        ".label{font:14px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;fill:#263238}",
        ".small{font:12px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;fill:#546e7a}",
        ".topic{fill:#e3f2fd;stroke:#1e88e5;stroke-width:1.4}",
        ".note{fill:#fff8e1;stroke:#f9a825;stroke-width:1.4}",
        ".radio{fill:#e8f5e9;stroke:#43a047;stroke-width:1.4}",
        ".edge{stroke:#90a4ae;stroke-width:1.4;fill:none;marker-end:url(#arrow)}",
        ".faint{stroke:#cfd8dc;stroke-width:1.1;fill:none;marker-end:url(#arrow)}",
        "a:hover rect{stroke-width:2.4}",
        "]]></style>",
    ]

    for note_index, note in enumerate(notes):
        y2 = note_y[note_index]
        for tag in note.tags:
            if tag not in topic_index:
                continue
            y1 = topic_y[topic_index[tag]]
            lines.append(_edge(230, y1, 455, y2, css_class="edge"))
        if radio_link:
            lines.append(_edge(665, y2, 850, radio_y, css_class="faint"))

    lines.append(_graph_heading("Topics", 70, 48))
    for index, tag in enumerate(topic_tags):
        href = topic_links.get(tag)
        lines.append(
            _node(
                x=50,
                y=topic_y[index] - 28,
                width=180,
                height=56,
                title=tag,
                subtitle="topic",
                css_class="topic",
                href=href,
            )
        )

    lines.append(_graph_heading("News Notes", 420, 48))
    for index, note in enumerate(notes):
        href = note_links[index] if index < len(note_links) else None
        lines.append(
            _node(
                x=410,
                y=note_y[index] - 36,
                width=255,
                height=72,
                title=note.title,
                subtitle=f"{note.source} / score {note.score}",
                css_class="note",
                href=href,
            )
        )

    lines.append(_graph_heading("Output", 840, 48))
    lines.append(
        _node(
            x=830,
            y=radio_y - 34,
            width=210,
            height=68,
            title="Daily Radio Script",
            subtitle="TTS-ready briefing",
            css_class="radio",
            href=radio_link,
        )
    )
    lines.extend(["</svg>", "</div>"])
    return "\n".join(lines)


def find_latest_wiki_run(wiki_dir: Path) -> Path | None:
    if not wiki_dir.exists():
        return None
    dated_dirs = sorted(
        path
        for path in wiki_dir.iterdir()
        if path.is_dir() and _is_date_dir(path)
    )
    if not dated_dirs:
        return None
    latest_day = dated_dirs[-1]
    run_dirs = sorted(path for path in latest_day.iterdir() if path.is_dir())
    if run_dirs:
        return run_dirs[-1]
    return latest_day


def _preview_run_dir(latest_run_dir: Path, wiki_dir: Path) -> Path:
    try:
        return latest_run_dir.relative_to(wiki_dir)
    except ValueError:
        return Path(latest_run_dir.name)


def _copy_markdown_files(source_dir: Path, destination_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for source in sorted(path for path in source_dir.glob("*.md") if path.is_file()):
        destination = destination_dir / source.name
        shutil.copyfile(source, destination)
        paths.append(destination)
    return paths


def _load_processed_items(path: Path | None) -> list[NewsItem]:
    if path is None or not path.exists():
        return []
    try:
        return load_raw_items(path)
    except (OSError, ValueError):
        return []


def _column_positions(count: int, height: int) -> list[int]:
    if count <= 0:
        return []
    top = 130
    bottom = height - 90
    if count == 1:
        return [(top + bottom) // 2]
    step = (bottom - top) / (count - 1)
    return [round(top + step * index) for index in range(count)]


def _edge(x1: int, y1: int, x2: int, y2: int, css_class: str) -> str:
    midpoint = (x1 + x2) // 2
    return (
        f'<path class="{css_class}" '
        f'd="M{x1},{y1} C{midpoint},{y1} {midpoint},{y2} {x2},{y2}" />'
    )


def _graph_heading(label: str, x: int, y: int) -> str:
    return f'<text class="small" x="{x}" y="{y}">{escape(label)}</text>'


def _node(
    x: int,
    y: int,
    width: int,
    height: int,
    title: str,
    subtitle: str,
    css_class: str,
    href: str | None = None,
) -> str:
    title_lines = _wrap_label(title, max_chars=30 if width > 220 else 18)
    escaped_subtitle = escape(subtitle)
    content = [
        f'<rect class="{css_class}" x="{x}" y="{y}" width="{width}" height="{height}" rx="10" />',
    ]
    text_y = y + 24
    for line in title_lines[:2]:
        content.append(f'<text class="label" x="{x + 14}" y="{text_y}">{escape(line)}</text>')
        text_y += 18
    content.append(f'<text class="small" x="{x + 14}" y="{y + height - 13}">{escaped_subtitle}</text>')
    inner = "\n".join(content)
    if href:
        return f'<a href="{escape(href)}">\n{inner}\n</a>'
    return inner


def _wrap_label(value: str, max_chars: int) -> list[str]:
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_chars:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [value]


def _reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _is_date_dir(path: Path) -> bool:
    name = path.name
    return len(name) == 10 and name[4] == "-" and name[7] == "-"


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
