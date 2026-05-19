"""Optional local speech editing pass for generated TTS text."""

from __future__ import annotations

import json
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from ai_signal_radio.tts.voicevox import (
    SpeechSegment,
    parse_speech_segments,
    render_speech_segments,
)

Transport = Callable[[Request, int], bytes]


class OllamaSpeechEditor:
    """Rewrite local radio speech text for easier listening.

    This editor is optional and local-first. It calls a user-specified local
    Ollama endpoint only when explicitly selected by the CLI or run script.
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

    def edit(self, speech_text: str) -> str:
        if not speech_text.strip():
            return speech_text
        segments = parse_speech_segments(speech_text)
        if segments:
            edited_segments = [
                SpeechSegment(text=self._edit_plain_text(segment.text), speaker=segment.speaker)
                for segment in segments
            ]
            return render_speech_segments(edited_segments)
        return self._edit_plain_text(speech_text)

    def _edit_plain_text(self, speech_text: str) -> str:
        fallback = speech_text.rstrip()
        payload = {
            "model": self.model,
            "prompt": _build_prompt(speech_text),
            "stream": False,
            "options": {"temperature": 0.1},
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
            edited = _clean_response(str(response.get("response", "")))
        except (json.JSONDecodeError, KeyError, URLError, TimeoutError, OSError) as exc:
            print(f"warning: Ollama speech editor failed: {exc}; using deterministic TTS text")
            return fallback

        if len(edited) < max(6, len(fallback) // 12):
            print("warning: Ollama speech editor returned too little text; using deterministic TTS text")
            return fallback
        return edited


def _default_transport(request: Request, timeout_seconds: int) -> bytes:
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def _build_prompt(speech_text: str) -> str:
    return f"""あなたは日本語ラジオ台本の発話編集者です。
入力はすでに TTS 用に正規化された日本語テキストです。
意味、事実、数値、出典、speaker 構造は変えないでください。
出力は読み上げる本文だけにしてください。説明やMarkdownコードブロックは禁止です。

編集方針:
- 1文を短くし、耳で追いやすい自然な日本語にする。
- 英字の固有名詞が残っていれば、必要に応じて読みやすいカタカナにする。
- 箇条書きの記号や見出し語を、発話として自然な接続にする。
- 断定しすぎず、元の情報量を増やさない。

入力:
{speech_text}
"""


def _clean_response(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("text").removeprefix("plaintext").strip()
    return cleaned.rstrip()
