"""Minimal VOICEVOX client.

VOICEVOX is optional for the MVP. The demo command does not use this client.
"""

from __future__ import annotations

from dataclasses import dataclass
import io
import json
import re
import wave
import html
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml


@dataclass(frozen=True)
class SpeechSegment:
    text: str
    speaker: int


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
        chunks = split_for_tts_text(text)
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

    def synthesize_segments_to_wav(
        self,
        segments: list[SpeechSegment],
        output_path: Path,
        speed_scale: float = 1.15,
        pitch_scale: float = 0.0,
        intonation_scale: float = 1.0,
    ) -> Path:
        audio_chunks: list[bytes] = []
        for segment in segments:
            for chunk in split_for_tts_text(segment.text):
                audio_chunks.append(
                    self.synthesis(
                        self.audio_query(
                            chunk,
                            segment.speaker,
                            speed_scale=speed_scale,
                            pitch_scale=pitch_scale,
                            intonation_scale=intonation_scale,
                        ),
                        segment.speaker,
                    )
                )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        if len(audio_chunks) == 1:
            output_path.write_bytes(audio_chunks[0])
        else:
            _write_joined_wav(audio_chunks, output_path)
        return output_path


PronunciationPairs = tuple[tuple[str, str], ...]
DEFAULT_TECHNICAL_PRONUNCIATIONS: PronunciationPairs = (
    ("Hacker News", "ハッカーニュース"),
    ("AWS Bedrock", "エーダブリューエス ベッドロック"),
    ("Vercel AI SDK", "バーセル エーアイ エスディーケー"),
    ("Hugging Face", "ハギングフェイス"),
    ("LangGraph", "ランググラフ"),
    ("CI/CD", "シーアイ シーディー"),
    ("VOICEVOX", "ボイスボックス"),
    ("OpenHarness", "オープンハーネス"),
    ("OpenAI", "オープンエーアイ"),
    ("Anthropic", "アンソロピック"),
    ("Gemini", "ジェミニ"),
    ("Android", "アンドロイド"),
    ("SQLite", "エスキューライト"),
    ("Postgres", "ポストグレス"),
    ("Redis", "レディス"),
    ("Ollama", "オラマ"),
    ("Claude", "クロード"),
    ("arXiv", "アーカイブ"),
    ("LLM", "エルエルエム"),
    ("API", "エーピーアイ"),
    ("SDK", "エスディーケー"),
    ("OS", "オーエス"),
    ("QA", "キューエー"),
    ("Host", "ホスト"),
    ("Analyst", "アナリスト"),
    ("AI", "エーアイ"),
)


def load_pronunciation_profile(path: Path | None) -> PronunciationPairs:
    """Load context-specific pronunciation replacements from YAML.

    The profile is intentionally explicit and optional. Different domains can
    read the same term differently, so this module does not keep a global
    dictionary.
    """

    if path is None:
        return ()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = raw.get("pronunciations", raw)
    if not isinstance(entries, list):
        raise ValueError("pronunciation profile must be a list or contain a pronunciations list")

    pairs: list[tuple[str, str]] = []
    for entry in entries:
        pair = _pronunciation_pair(entry)
        if pair:
            pairs.append(pair)
    return tuple(pairs)


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
        line = normalize_symbols_for_tts(line)
        lines.append(normalize_for_tts(line, pronunciations))
    return "\n".join(lines)


def markdown_to_speech_segments(
    markdown: str,
    default_speaker: int,
    role_speakers: dict[str, int],
    pronunciations: PronunciationPairs = (),
) -> list[SpeechSegment]:
    segments: list[SpeechSegment] = []
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
        speaker = default_speaker
        role_match = re.match(r"^(Host|Analyst):\s*(.+)$", line, flags=re.IGNORECASE)
        if role_match:
            role = role_match.group(1).lower()
            speaker = role_speakers.get(role, default_speaker)
            line = role_match.group(2)
        line = normalize_symbols_for_tts(line)
        text = normalize_for_tts(line, pronunciations)
        if text:
            segments.append(SpeechSegment(text=text, speaker=speaker))
    return _merge_adjacent_segments(segments)


def render_speech_segments(segments: list[SpeechSegment]) -> str:
    """Render speaker-aware speech text for review and later synthesis."""

    blocks = [
        f"[speaker={segment.speaker}]\n{segment.text.strip()}"
        for segment in segments
        if segment.text.strip()
    ]
    return "\n\n".join(blocks).strip()


def parse_speech_segments(text: str) -> list[SpeechSegment]:
    """Parse the speaker block format emitted by render_speech_segments."""

    segments: list[SpeechSegment] = []
    current_speaker: int | None = None
    current_lines: list[str] = []
    saw_header = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        header = re.match(r"^\[speaker=(\d+)\]$", line)
        if header:
            if current_speaker is not None and current_lines:
                segments.append(
                    SpeechSegment(text="\n".join(current_lines).strip(), speaker=current_speaker)
                )
            current_speaker = int(header.group(1))
            current_lines = []
            saw_header = True
            continue
        if current_speaker is None:
            if line:
                return []
            continue
        current_lines.append(raw_line.rstrip())

    if current_speaker is not None and current_lines:
        segments.append(SpeechSegment(text="\n".join(current_lines).strip(), speaker=current_speaker))
    return [segment for segment in segments if segment.text] if saw_header else []


def normalize_symbols_for_tts(text: str) -> str:
    """Remove Markdown and punctuation noise before local TTS."""

    converted = html.unescape(text)
    converted = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", converted)
    converted = re.sub(r"https?://\S+", "リンク", converted)
    converted = re.sub(r"^\d+\.\s*", "", converted)
    converted = converted.replace("&", "アンド")
    converted = re.sub(r"\s*[:：]\s*", "、", converted)
    converted = re.sub(r"\s*[,，]\s*", "、", converted)
    converted = re.sub(r"[()（）]", "、", converted)
    converted = re.sub(r"[\"“”]", "", converted)
    converted = re.sub(r"、{2,}", "、", converted)
    converted = re.sub(r"\s+", " ", converted)
    converted = re.sub(r"\s*([、。！？])\s*", r"\1", converted)
    return converted.strip(" 、")


def normalize_for_tts(text: str, pronunciations: PronunciationPairs = ()) -> str:
    """Apply context profile first, then conservative technical defaults."""

    converted = apply_pronunciations(text, pronunciations)
    user_terms = {term for term, _ in pronunciations}
    defaults = tuple(
        (term, reading)
        for term, reading in DEFAULT_TECHNICAL_PRONUNCIATIONS
        if term not in user_terms
    )
    return apply_pronunciations(converted, defaults)


def apply_pronunciations(text: str, pronunciations: PronunciationPairs = ()) -> str:
    converted = text
    for term, reading in pronunciations:
        converted = converted.replace(term, reading)
    return converted


def _merge_adjacent_segments(segments: list[SpeechSegment]) -> list[SpeechSegment]:
    merged: list[SpeechSegment] = []
    for segment in segments:
        if merged and merged[-1].speaker == segment.speaker:
            previous = merged[-1]
            merged[-1] = SpeechSegment(
                text=f"{previous.text}\n{segment.text}",
                speaker=previous.speaker,
            )
        else:
            merged.append(segment)
    return merged


def _pronunciation_pair(entry: Any) -> tuple[str, str] | None:
    if isinstance(entry, dict):
        term = str(entry.get("term", "")).strip()
        reading = str(entry.get("reading", "")).strip()
    elif isinstance(entry, (list, tuple)) and len(entry) == 2:
        term = str(entry[0]).strip()
        reading = str(entry[1]).strip()
    else:
        return None
    if not term or not reading:
        return None
    return term, reading


def split_for_tts_text(text: str, max_chars: int = 240) -> list[str]:
    units = [unit.strip() for unit in re.split(r"(?<=[。！？\n])", text) if unit.strip()]
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


def split_for_tts(text: str, max_chars: int = 240) -> list[str]:
    """Backward-compatible wrapper for callers that still pass Markdown."""

    return split_for_tts_text(markdown_to_speech_text(text), max_chars=max_chars)


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
