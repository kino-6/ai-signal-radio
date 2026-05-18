"""Spoken headline helpers for radio scripts."""

from __future__ import annotations

import re

from ai_signal_radio.models import WikiNote

KNOWN_HEADLINE_TERMS = (
    "AWS Bedrock",
    "OpenHarness",
    "Probus",
    "Torrix",
    "Sova AI",
    "Sova",
    "Vercel AI SDK",
    "LangGraph",
    "Hugging Face",
    "OpenAI",
    "Anthropic",
    "Google",
    "Gemini",
)
GENERIC_CLUSTER_LABELS = {
    "AI",
    "Android",
    "Assistant",
    "Coding",
    "Google",
    "LangGraph",
    "Observability",
}
TITLE_REWRITE_RULES = (
    (
        re.compile(r"google banned .*mobile ai agent", re.IGNORECASE),
        "Sova AIのモバイルエージェントがGoogle Playで却下",
    ),
    (re.compile(r"android ai agent-assistant", re.IGNORECASE), "Sova AIのAndroidエージェント"),
    (
        re.compile(r"prompt caching miss", re.IGNORECASE),
        "AWS Bedrockのプロンプトキャッシュ不備で高額請求",
    ),
    (
        re.compile(r"torrix.*llm observability", re.IGNORECASE),
        "Torrix: SQLiteで動くLLM監視ツール",
    ),
    (
        re.compile(r"openharness.*coding agent", re.IGNORECASE),
        "OpenHarness: 任意のLLMで動くターミナルコーディングエージェント",
    ),
    (re.compile(r"probus.*vuln scanner", re.IGNORECASE), "Probus: AI脆弱性スキャナー"),
    (
        re.compile(r"model evaluation harness.*benchmark", re.IGNORECASE),
        "AI評価ベンチマークの更新",
    ),
    (
        re.compile(r"agent memory.*long tasks", re.IGNORECASE),
        "長いタスク向けエージェントメモリ研究",
    ),
    (
        re.compile(r"voicevox.*narration workflow", re.IGNORECASE),
        "VOICEVOX読み上げワークフロー",
    ),
)


def spoken_headline(note: WikiNote) -> str:
    """Return a compact headline that is easier for local TTS to read."""

    title = radio_title(note.title)
    if not _is_tts_unfriendly_english(title):
        return title

    rewritten = rewrite_known_headline(title)
    if rewritten:
        return rewritten

    summary = _first_sentence(note.fact_summary).rstrip("。.!?！？")
    if not summary or not _contains_japanese(summary):
        return title

    summary = shorten_headline(summary)
    subject = headline_subject(note)
    if subject and not summary.startswith(subject):
        return f"{subject}: {summary}"
    return summary


def radio_title(title: str) -> str:
    """Make raw collected titles less awkward for spoken briefings."""

    text = " ".join(title.split())
    text = re.sub(r"^(Show|Ask|Tell) HN:\s*", "", text, flags=re.IGNORECASE)
    text = text.replace("doesnt", "doesn't")
    text = re.sub(r"\s*,\s*", "、", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -")


def rewrite_known_headline(title: str) -> str:
    for pattern, replacement in TITLE_REWRITE_RULES:
        if pattern.search(title):
            return replacement
    return ""


def shorten_headline(text: str, max_chars: int = 56) -> str:
    compact = text.strip()
    for separator in ("。", "です", "ます", "でした", "ました", "であり", "により", "によって"):
        if separator in compact:
            candidate = compact.split(separator, 1)[0].strip()
            if 12 <= len(candidate) <= max_chars:
                return candidate
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip("、。 ") + "…"


def headline_subject(note: WikiNote) -> str:
    label = note.topic_cluster_label.strip()
    if label and label not in GENERIC_CLUSTER_LABELS and len(label) <= 32:
        if label == "Sova":
            return "Sova AI"
        return label

    title = radio_title(note.title)
    for term in KNOWN_HEADLINE_TERMS:
        if term.lower() in title.lower():
            return "Sova AI" if term == "Sova" else term
    return ""


def _first_sentence(text: str) -> str:
    stripped = " ".join(text.split())
    if not stripped:
        return ""
    end_indexes = [index for index, char in enumerate(stripped) if char in "。.!?"]
    if end_indexes:
        return stripped[: end_indexes[0] + 1]
    return stripped


def _is_tts_unfriendly_english(text: str) -> bool:
    letters = re.findall(r"[A-Za-z]", text)
    if len(letters) < 8:
        return False
    ascii_chars = [char for char in text if char.isascii() and not char.isspace()]
    non_space = [char for char in text if not char.isspace()]
    ascii_ratio = len(ascii_chars) / len(non_space) if non_space else 0.0
    return ascii_ratio >= 0.55


def _contains_japanese(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text))
