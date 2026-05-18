"""Optional local Ollama summarizer."""

from __future__ import annotations

import json
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from ai_signal_radio.models import NewsItem, WikiNote
from ai_signal_radio.processors.wiki_writer import note_from_item

Transport = Callable[[Request, int], bytes]


class OllamaSummarizer:
    """Generate WikiNote fields with a local Ollama model.

    This class is only used when explicitly selected by the CLI. Tests inject a
    fake transport, so no hidden network calls are required.
    """

    def __init__(
        self,
        model: str = "gemma4:latest",
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: int = 120,
        transport: Transport | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport or _default_transport

    def __call__(self, item: NewsItem) -> WikiNote:
        fallback = note_from_item(item)
        prompt = _build_prompt(item)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        }
        request = Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            raw = self.transport(request, self.timeout_seconds)
            response = json.loads(raw.decode("utf-8"))
            generated = json.loads(response.get("response", "{}"))
        except (json.JSONDecodeError, KeyError, URLError, TimeoutError, OSError) as exc:
            print(f"warning: Ollama summarizer failed for {item.title}: {exc}; using fallback")
            return fallback

        return WikiNote(
            title=item.title,
            source=item.source,
            source_url=item.url,
            source_type=item.source_type,
            published_at=item.published_at,
            collected_at=item.collected_at,
            tags=item.tags or ("ai",),
            fact_summary=_text_field(generated.get("fact_summary"), fallback.fact_summary),
            interpretation=_text_field(generated.get("interpretation"), fallback.interpretation),
            action_items=_list_field(generated.get("action_items"), fallback.action_items),
            score_reasons=fallback.score_reasons,
            source_coverage=_text_field(generated.get("source_coverage"), fallback.source_coverage),
            dedupe_notes=fallback.dedupe_notes,
            open_questions=_list_field(generated.get("open_questions"), fallback.open_questions),
            score=item.score,
        )


def _default_transport(request: Request, timeout_seconds: int) -> bytes:
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def _build_prompt(item: NewsItem) -> str:
    return f"""あなたはAIニュースをLLM向けwikiに整理する編集者です。
入力された情報だけを根拠にし、不明点は推測で埋めないでください。
日本語で、読み上げにも使いやすい短い文にしてください。

Return only JSON with these keys:
- fact_summary: 事実だけを1-2文で要約。根拠が不足する場合は「不明」と書く。
- interpretation: AI開発者・研究者にとっての意味を1-2文で説明。
- action_items: 次に確認する行動を2個、短い日本語配列で返す。
- source_coverage: この情報が単一ソースか、公式/研究/コミュニティ情報かを1文で説明。
- open_questions: 追加確認すべき問いを1-2個、短い日本語配列で返す。

Title: {item.title}
Source: {item.source}
Source type: {item.source_type}
URL: {item.url}
Published at: {item.published_at.isoformat()}
Summary: {item.summary}
Content: {item.content}
Tags: {", ".join(item.tags)}
Score: {item.score}
"""


def _text_field(value: object, fallback: str, max_chars: int = 320) -> str:
    text = str(value).strip() if isinstance(value, str) else ""
    if not text:
        text = fallback
    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "…"
    return text


def _list_field(value: object, fallback: tuple[str, ...], max_item_chars: int = 120) -> tuple[str, ...]:
    if isinstance(value, list):
        items = tuple(
            _text_field(item, "", max_chars=max_item_chars)
            for item in value
            if isinstance(item, str) and item.strip()
        )
        if items:
            return items
    return fallback
