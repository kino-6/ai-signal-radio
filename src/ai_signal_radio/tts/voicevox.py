"""Minimal VOICEVOX client."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class VoicevoxClient:
    def __init__(self, endpoint: str = "http://127.0.0.1:50021", speaker: int = 1) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.speaker = speaker

    def synthesize_to_file(self, text: str, output_path: Path) -> Path:
        query = self._audio_query(text)
        audio = self._synthesis(query)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio)
        return output_path

    def _audio_query(self, text: str) -> dict:
        params = urlencode({"text": text, "speaker": str(self.speaker)})
        request = Request(f"{self.endpoint}/audio_query?{params}", method="POST")
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def _synthesis(self, query: dict) -> bytes:
        params = urlencode({"speaker": str(self.speaker)})
        body = json.dumps(query).encode("utf-8")
        request = Request(
            f"{self.endpoint}/synthesis?{params}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            return response.read()
