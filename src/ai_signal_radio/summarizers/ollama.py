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
            fact_summary=str(generated.get("fact_summary") or fallback.fact_summary).strip(),
            interpretation=str(generated.get("interpretation") or fallback.interpretation).strip(),
            action_items=_action_items(generated.get("action_items"), fallback.action_items),
            score=item.score,
        )


def _default_transport(request: Request, timeout_seconds: int) -> bytes:
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def _build_prompt(item: NewsItem) -> str:
    return f"""You are preparing a concise Japanese AI news wiki note.
Return only JSON with these keys:
- fact_summary: a factual Japanese summary in 1-2 sentences
- interpretation: why this matters for AI builders in 1-2 Japanese sentences
- action_items: 2 short Japanese action items as an array of strings

Title: {item.title}
Source: {item.source}
Source type: {item.source_type}
URL: {item.url}
Summary: {item.summary}
Content: {item.content}
Tags: {", ".join(item.tags)}
"""


def _action_items(value: object, fallback: tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(value, list):
        items = tuple(str(item).strip() for item in value if str(item).strip())
        if items:
            return items
    return fallback
