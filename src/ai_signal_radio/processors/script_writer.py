"""Radio-style script generation from wiki notes."""

from __future__ import annotations

from pathlib import Path

from ai_signal_radio.models import WikiNote


def write_script(notes: list[WikiNote], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_script(notes), encoding="utf-8")
    return output_path


def render_script(notes: list[WikiNote]) -> str:
    lines = [
        "# Daily AI Signal Radio",
        "",
        "こんにちは。今日のAIニュースです。",
        "",
        f"今日の注目トピックは {len(notes)} 件です。",
        "",
    ]

    if not notes:
        lines.extend(
            [
                "今日はまだ紹介できるトピックがありません。",
                "",
                "それでは、今日もよい開発を。",
                "",
            ]
        )
        return "\n".join(lines)

    for index, note in enumerate(notes, start=1):
        lines.extend(
            [
                f"## {index}. {note.title}",
                "",
                f"取得元は {note.source} です。",
                "",
                note.fact_summary,
                "",
                note.interpretation,
                "",
            ]
        )

    lines.extend(["それでは、今日もよい開発を。", ""])
    return "\n".join(lines)
