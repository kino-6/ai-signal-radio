"""Minimal VOICEVOX client.

VOICEVOX is optional for the MVP. The demo command does not use this client.
"""

from __future__ import annotations

import io
import json
import re
import wave
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class VoicevoxClient:
    def __init__(self, base_url: str = "http://127.0.0.1:50021") -> None:
        self.base_url = base_url.rstrip("/")

    def healthcheck(self) -> bool:
        request = Request(f"{self.base_url}/version", method="GET")
        try:
            with urlopen(request, timeout=5) as response:
                return response.status == 200
        except OSError:
            return False

    def audio_query(
        self,
        text: str,
        speaker: int,
        speed_scale: float = 1.0,
        pitch_scale: float = 0.0,
        intonation_scale: float = 1.0,
    ) -> dict:
        params = urlencode({"text": text, "speaker": str(speaker)})
        request = Request(f"{self.base_url}/audio_query?{params}", method="POST")
        with urlopen(request, timeout=30) as response:
            query = json.loads(response.read().decode("utf-8"))
        query["speedScale"] = speed_scale
        query["pitchScale"] = pitch_scale
        query["intonationScale"] = intonation_scale
        return query

    def synthesis(self, query: dict, speaker: int) -> bytes:
        params = urlencode({"speaker": str(speaker)})
        body = json.dumps(query).encode("utf-8")
        request = Request(
            f"{self.base_url}/synthesis?{params}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            return response.read()

    def synthesize_to_wav(
        self,
        text: str,
        output_path: Path,
        speaker: int = 3,
        speed_scale: float = 1.15,
        pitch_scale: float = 0.0,
        intonation_scale: float = 1.0,
    ) -> Path:
        chunks = split_for_tts(text)
        audio_chunks = [
            self.synthesis(
                self.audio_query(
                    chunk,
                    speaker,
                    speed_scale=speed_scale,
                    pitch_scale=pitch_scale,
                    intonation_scale=intonation_scale,
                ),
                speaker,
            )
            for chunk in chunks
        ]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if len(audio_chunks) == 1:
            output_path.write_bytes(audio_chunks[0])
        else:
            _write_joined_wav(audio_chunks, output_path)
        return output_path


PronunciationPairs = tuple[tuple[str, str], ...]


def markdown_to_speech_text(markdown: str, pronunciations: PronunciationPairs = ()) -> str:
    lines: list[str] = []
    in_frontmatter = False
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter or not line:
            continue
        line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"^[-*]\s+", "", line)
        line = re.sub(r"`([^`]+)`", r"\1", line)
        lines.append(apply_pronunciations(line, pronunciations))
    return "\n".join(lines)


def apply_pronunciations(text: str, pronunciations: PronunciationPairs = ()) -> str:
    converted = text
    for term, reading in pronunciations:
        converted = converted.replace(term, reading)
    return converted


def split_for_tts(text: str, max_chars: int = 240) -> list[str]:
    normalized = markdown_to_speech_text(text)
    units = [unit.strip() for unit in re.split(r"(?<=[。！？\n])", normalized) if unit.strip()]
    chunks: list[str] = []
    current = ""
    for unit in units:
        if current and len(current) + len(unit) + 1 > max_chars:
            chunks.append(current)
            current = unit
        else:
            current = f"{current}\n{unit}".strip() if current else unit
    if current:
        chunks.append(current)
    return chunks or ["読み上げるテキストがありません。"]


def _write_joined_wav(audio_chunks: list[bytes], output_path: Path) -> None:
    params = None
    frames: list[bytes] = []
    for audio in audio_chunks:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            if params is None:
                params = wav.getparams()
            elif wav.getparams()[:3] != params[:3]:
                raise ValueError("VOICEVOX returned incompatible wav chunks")
            frames.append(wav.readframes(wav.getnframes()))

    if params is None:
        raise ValueError("No audio chunks to write")

    with wave.open(str(output_path), "wb") as output:
        output.setparams(params)
        for frame in frames:
            output.writeframes(frame)
