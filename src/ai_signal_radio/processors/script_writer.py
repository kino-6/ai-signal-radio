"""Radio-style script generation from wiki notes."""

from __future__ import annotations

from pathlib import Path

from ai_signal_radio.models import WikiNote

ScriptStyle = str


def write_script(notes: list[WikiNote], output_path: Path, style: ScriptStyle = "standard") -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_script(notes, style=style), encoding="utf-8")
    return output_path


def render_script(notes: list[WikiNote], style: ScriptStyle = "standard") -> str:
    if style not in {"short", "standard", "detailed"}:
        raise ValueError(f"Unsupported script style: {style}")

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
            ]
        )
        if style in {"standard", "detailed"}:
            lines.extend([note.interpretation, ""])
        if style == "detailed":
            action = note.action_items[0] if note.action_items else "元情報を確認しましょう。"
            lines.extend([f"次のアクションは、{action}", ""])

    lines.extend(["それでは、今日もよい開発を。", ""])
    return "\n".join(lines)
