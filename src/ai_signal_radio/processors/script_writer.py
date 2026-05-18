"""Radio-style script generation from wiki notes."""

from __future__ import annotations

from pathlib import Path
import re

from ai_signal_radio.models import WikiNote
from ai_signal_radio.processors.headline import spoken_headline

ScriptStyle = str
SUPPORTED_STYLES = {"short", "standard", "detailed", "briefing", "dialogue"}
BRIEFING_MAIN_TOPIC_LIMIT = 2


def write_script(notes: list[WikiNote], output_path: Path, style: ScriptStyle = "standard") -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_script(notes, style=style), encoding="utf-8")
    return output_path


def render_script(notes: list[WikiNote], style: ScriptStyle = "standard") -> str:
    if style not in SUPPORTED_STYLES:
        raise ValueError(f"Unsupported script style: {style}")

    if style == "briefing":
        return render_briefing_script(notes)
    if style == "dialogue":
        return render_dialogue_script(notes)

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


def render_briefing_script(notes: list[WikiNote]) -> str:
    display_notes = representative_notes(notes)
    lines = [
        "# Daily AI Signal Radio",
        "",
        "こんにちは。今日のAIニュースです。",
        "",
        f"今日の注目トピックは {len(display_notes)} 件です。",
        "",
    ]

    if not display_notes:
        lines.extend(
            [
                "今日はまだ紹介できるトピックがありません。",
                "",
                "それでは、今日もよい開発を。",
                "",
            ]
        )
        return "\n".join(lines)

    if len(display_notes) != len(notes):
        lines.extend([f"収集した {len(notes)} 件を、重複する話題をまとめて {len(display_notes)} トピックに整理しました。", ""])

    focus_line = daily_focus_line(display_notes)
    if focus_line:
        lines.extend([focus_line, ""])

    bias_line = source_bias_line(display_notes)
    if bias_line:
        lines.extend([bias_line, ""])

    main_notes = display_notes[:BRIEFING_MAIN_TOPIC_LIMIT]
    quick_notes = display_notes[BRIEFING_MAIN_TOPIC_LIMIT:]
    if quick_notes:
        lines.extend(
            [
                f"まずは上位 {len(main_notes)} 件だけを押さえて、そのあと {len(quick_notes)} 件を一言で拾います。",
                "",
            ]
        )
    else:
        lines.extend(["今日は上位トピックを順番に見ていきます。", ""])

    for index, note in enumerate(main_notes, start=1):
        lines.extend(
            [
                f"## {index}. {radio_headline(note)}",
                "",
                source_line(note),
                "",
                one_line_takeaway(note),
                "",
                why_it_matters_line(note),
                "",
                listen_action_line(note),
                "",
            ]
        )

    if quick_notes:
        lines.extend(["## 一言ニュース", ""])
        for note in quick_notes:
            lines.extend(
                [
                    quick_news_line(note),
                ]
            )
        lines.append("")

    candidate = deep_dive_candidate(display_notes)
    if candidate:
        lines.extend(
            [
                "## 今日の深掘り候補",
                "",
                f"{radio_headline(candidate)}を深掘り候補にします。",
                "",
                daily_deep_dive_reason(candidate),
                "",
            ]
        )

    lines.extend(["今日の実装観点は、気になった話題を読むだけで終わらせず、小さく試せる形に分解することです。", ""])
    lines.extend(["それでは、今日もよい開発を。", ""])
    return "\n".join(lines)


def render_dialogue_script(notes: list[WikiNote]) -> str:
    display_notes = representative_notes(notes)
    lines = [
        "# AI Signal Radio Deep Dive",
        "",
        "こんにちは。AI Signal Radio の深掘りです。",
        "",
    ]
    if not display_notes:
        lines.extend(["今日は深掘りできるトピックがありません。", "", "それでは、今日もよい開発を。", ""])
        return "\n".join(lines)

    note = display_notes[0]
    question = first_open_question(note)
    lines.extend(
        [
            f"今日のテーマは「{radio_headline(note)}」です。",
            "",
            "Analyst: まず、これは何が起きた話ですか？",
            "",
            f"Host: {source_line(note)} {one_line_takeaway(note)}",
            "",
            "## 事実",
            "",
            f"Host: {fact_line(note)}",
            "",
            "## 解釈",
            "",
            "Analyst: それは、AI開発者にとってなぜ重要なんでしょう？",
            "",
            f"Host: {why_it_matters_answer(note)}",
            "",
            "Analyst: 深掘り候補にした理由も確認しておきたいです。",
            "",
            f"Host: {deep_dive_reason(note)}",
            "",
            "## 試す価値",
            "",
            "Analyst: では、次にどこを見るとよさそうですか？",
            "",
            f"Host: {listen_action_line(note)}",
            "",
        ]
    )
    if question:
        lines.extend(
            [
                "## 未確認事項",
                "",
                "Analyst: まだ確認が必要な点はありますか？",
                "",
                f"Host: {question}",
                "",
            ]
        )
    if note.related_titles:
        lines.extend(
            [
                f"Host: なお、この話題は関連投稿 {note.topic_cluster_size} 件をまとめて見ています。",
                "",
            ]
        )
    lines.extend(["この深掘りはここまでです。", "", "それでは、今日もよい開発を。", ""])
    return "\n".join(lines)


def quick_news_line(note: WikiNote) -> str:
    headline = radio_headline(note)
    summary = one_line_takeaway(note)
    if _same_spoken_content(headline, summary):
        return f"- {headline}。{source_line(note)}"
    return f"- {headline}。{source_line(note)} {summary}"


def source_line(note: WikiNote) -> str:
    label = source_label(note)
    suffix = ""
    if note.topic_cluster_size > 1 and note.topic_cluster_representative:
        suffix = f"関連投稿 {note.topic_cluster_size} 件をまとめています。"
    if note.source_type == "arxiv":
        return _join_source_parts(f"{label} の研究情報です。", suffix)
    if note.source_type in {"hackernews", "hn"} or "hacker" in note.source.lower():
        return _join_source_parts(f"{label} より。", suffix)
    if note.source_type == "rss":
        return _join_source_parts(f"{label} からのニュースです。", suffix)
    return _join_source_parts(f"{label} より。", suffix)


def source_bias_line(notes: list[WikiNote]) -> str:
    if len(notes) < 2:
        return ""
    counts: dict[str, int] = {}
    for note in notes:
        counts[note.source_type] = counts.get(note.source_type, 0) + 1
    source_type, count = max(counts.items(), key=lambda item: item[1])
    if count / len(notes) < 0.75:
        return ""
    label = source_type_label(source_type)
    return f"今日は {label} 中心の回です。別ソースの取得状況は取得ログに残しています。"


def source_type_label(source_type: str) -> str:
    normalized = source_type.lower()
    if normalized == "hackernews":
        return "Hacker News"
    if normalized == "arxiv":
        return "arXiv"
    if normalized == "rss":
        return "RSS"
    return source_type or "単一ソース"


def daily_focus_line(notes: list[WikiNote]) -> str:
    candidate = deep_dive_candidate(notes)
    if not candidate:
        return ""
    takeaway = one_line_takeaway(candidate)
    headline = radio_headline(candidate)
    if _same_spoken_content(headline, takeaway):
        return f"今日はこれだけ覚えてください。{headline}です。"
    return f"今日はこれだけ覚えてください。{headline}。{takeaway}"


def deep_dive_candidate(notes: list[WikiNote]) -> WikiNote | None:
    if not notes:
        return None
    return max(notes, key=deep_dive_score)


def deep_dive_score(note: WikiNote) -> tuple[float, int, int, float]:
    has_open_question = any(question.strip() and question.strip() != "不明" for question in note.open_questions)
    return (
        note.score,
        note.topic_cluster_size,
        1 if has_open_question else 0,
        note.published_at.timestamp(),
    )


def deep_dive_reason(note: WikiNote) -> str:
    reasons: list[str] = []
    if note.topic_cluster_size > 1:
        reasons.append(f"関連投稿が {note.topic_cluster_size} 件あり、単発ではない動きに見える")
    source = source_type_label(note.source_type)
    if source:
        reasons.append(f"{source} 発で開発者の反応を追いやすい")
    score_reasons = [
        humanize_score_reason(reason)
        for reason in note.score_reasons
        if reason and reason != "不明"
    ]
    score_reasons = [reason for reason in score_reasons if reason]
    if score_reasons:
        reasons.append("、".join(score_reasons[:2]))
    elif note.score:
        reasons.append("重要度スコアが高い")
    if not reasons:
        reasons.append("今日の先頭トピックで、確認する価値がある")
    return "、".join(reasons) + "であるためです。"


def daily_deep_dive_reason(note: WikiNote) -> str:
    reasons: list[str] = []
    if note.topic_cluster_size > 1:
        reasons.append("関連投稿が複数あります")
    if first_open_question(note):
        reasons.append("未確認の論点があります")
    if note.score >= 8:
        reasons.append("今日の中でも優先度が高いです")
    if not reasons:
        reasons.append("開発者目線で次に調べる価値があります")
    return "理由は、" + "。".join(reasons) + "。詳細は深掘り版で扱います。"


def humanize_score_reason(reason: str) -> str:
    if reason.startswith("keyword_matches="):
        return "AI関連キーワードの一致が多いこと"
    if reason.startswith("keyword_score="):
        return "AI関連キーワードの重みが高いこと"
    if reason.startswith("hn_points_bonus="):
        return "Hacker News で反応があること"
    if reason.startswith("official_source_bonus="):
        return "公式ソース由来の加点があること"
    if reason.startswith("research_bonus="):
        return "研究ソース由来の加点があること"
    return reason


def representative_notes(notes: list[WikiNote]) -> list[WikiNote]:
    seen_clusters: set[str] = set()
    representatives: list[WikiNote] = []
    for note in notes:
        cluster_id = note.topic_cluster_id
        if cluster_id and cluster_id in seen_clusters:
            continue
        if cluster_id:
            seen_clusters.add(cluster_id)
        if note.topic_cluster_size > 1 and not note.topic_cluster_representative:
            continue
        representatives.append(note)
    return representatives


def source_label(note: WikiNote) -> str:
    source_type = note.source_type.lower()
    source = note.source.strip()
    if source_type == "arxiv" or "arxiv" in source.lower():
        return "arXiv"
    if source_type in {"hackernews", "hn"} or "hacker" in source.lower():
        return "Hacker News"
    if source:
        return source
    return source_type or "unknown source"


def radio_headline(note: WikiNote) -> str:
    return note.spoken_title.strip() or spoken_headline(note)


def one_line_takeaway(note: WikiNote) -> str:
    return _ensure_sentence(note.one_line_takeaway) if note.one_line_takeaway else first_sentence(note.fact_summary)


def fact_line(note: WikiNote) -> str:
    if _contains_japanese(note.fact_summary):
        return first_sentence(note.fact_summary)
    return one_line_takeaway(note)


def why_it_matters_line(note: WikiNote) -> str:
    if note.why_it_matters:
        return _ensure_sentence(note.why_it_matters)
    return concise_interpretation_line(note)


def why_it_matters_answer(note: WikiNote) -> str:
    if note.why_it_matters:
        return _ensure_sentence(note.why_it_matters)
    if not note.interpretation.strip():
        return "元情報を確認して判断します。"
    interpretation = first_sentence(note.interpretation)
    return re.sub(r"^(この事例|このツール|これは|この動き)は、?", "", interpretation)


def listen_action_line(note: WikiNote) -> str:
    if note.listen_action:
        return _ensure_sentence(note.listen_action)
    return f"見るポイントは、{first_action(note)}"


def first_action(note: WikiNote) -> str:
    if note.action_items:
        return _ensure_sentence(note.action_items[0])
    return "元情報を確認することです。"


def concise_interpretation_line(note: WikiNote) -> str:
    if not note.interpretation.strip():
        return "意味合いは、元情報を確認して判断します。"
    interpretation = first_sentence(note.interpretation)
    interpretation = re.sub(r"^(この事例|このツール|これは|この動き)は、?", "", interpretation)
    return f"意味合いは、{interpretation}"


def first_open_question(note: WikiNote) -> str:
    for question in note.open_questions:
        normalized = question.strip()
        if normalized and normalized != "不明":
            return _ensure_sentence(normalized)
    return ""


def first_sentence(text: str) -> str:
    stripped = " ".join(text.split())
    if not stripped:
        return "詳細は元記事を確認しましょう。"
    end_indexes = [index for index, char in enumerate(stripped) if char in "。.!?"]
    if end_indexes:
        return _ensure_sentence(stripped[: end_indexes[0] + 1])
    return _ensure_sentence(stripped)


def _same_spoken_content(left: str, right: str) -> bool:
    left_norm = _normalize_spoken_text(left)
    right_norm = _normalize_spoken_text(right)
    return bool(left_norm and right_norm and (left_norm in right_norm or right_norm in left_norm))


def _normalize_spoken_text(text: str) -> str:
    return re.sub(r"\W+", "", text.lower())


def _contains_japanese(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text))


def _ensure_sentence(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if stripped[-1] in "。.!?！？":
        return stripped
    return f"{stripped}。"


def _join_source_parts(source: str, suffix: str) -> str:
    if not suffix:
        return source
    source = source.rstrip()
    if source[-1:] in "。.!?！？":
        return f"{source}{suffix}"
    return f"{source} {suffix}"
