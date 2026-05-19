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
    ("AI Signal Radio", "エーアイシグナルラジオ"),
    ("Daily", "デイリー"),
    ("Deep Dive", "ディープダイブ"),
    ("Hacker News", "ハッカーニュース"),
    ("AWS Bedrock", "エーダブリューエス ベッドロック"),
    ("Vercel AI SDK", "バーセル エーアイ エスディーケー"),
    ("Hugging Face", "ハギングフェイス"),
    ("Google Play", "グーグルプレイ"),
    ("LangGraph", "ランググラフ"),
    ("CI/CD", "シーアイ シーディー"),
    ("VOICEVOX", "ボイスボックス"),
    ("OpenHarness", "オープンハーネス"),
    ("Harness", "ハーネス"),
    ("ハナース", "ハーネス"),
    ("ハーンセス", "ハーネス"),
    ("OpenAI", "オープンエーアイ"),
    ("Anthropic", "アンソロピック"),
    ("Gemini", "ジェミニ"),
    ("Android", "アンドロイド"),
    ("Neovim", "ネオビム"),
    ("Flemma", "フレマ"),
    ("Probus", "プロバス"),
    ("Torrix", "トリックス"),
    ("Sova AI", "ソーバ エーアイ"),
    ("Sova", "ソーバ"),
    ("Axe", "アックス"),
    ("GitHub", "ギットハブ"),
    ("Google", "グーグル"),
    ("Unix", "ユニックス"),
    ("SQLite", "エスキューライト"),
    ("Postgres", "ポストグレス"),
    ("Redis", "レディス"),
    ("Ollama", "オラマ"),
    ("Claude", "クロード"),
    ("arXiv", "アーカイブ"),
    ("CLI", "シーエルアイ"),
    ("MB", "メガバイト"),
    ("LLM", "エルエルエム"),
    ("API", "エーピーアイ"),
    ("SDK", "エスディーケー"),
    ("OS", "オーエス"),
    ("OR", "オーアール"),
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
        lines.extend(_speech_lines_from_markdown_line(line, pronunciations))
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
        speaker = default_speaker
        role_match = re.match(r"^(Host|Analyst):\s*(.+)$", line, flags=re.IGNORECASE)
        if role_match:
            role = role_match.group(1).lower()
            speaker = role_speakers.get(role, default_speaker)
            line = role_match.group(2)
            speech_lines = _speech_lines_from_text(line, pronunciations)
        else:
            speech_lines = _speech_lines_from_markdown_line(line, pronunciations)
        if speech_lines:
            segments.append(SpeechSegment(text="\n".join(speech_lines), speaker=speaker))
    return _merge_adjacent_segments(segments)


def render_speech_segments(segments: list[SpeechSegment]) -> str:
    """Render speaker-aware speech text for review and later synthesis."""

    blocks = [
        f"[speaker={segment.speaker}]\n{segment.text.strip()}"
        for segment in segments
        if segment.text.strip()
    ]
    return "\n\n".join(blocks).strip()


def normalize_speech_text(text: str, pronunciations: PronunciationPairs = ()) -> str:
    """Normalize already edited speech text while preserving speaker blocks."""

    segments = parse_speech_segments(text)
    if segments:
        normalized_segments = [
            SpeechSegment(
                text=_plain_speech_text_from_text(segment.text, pronunciations),
                speaker=segment.speaker,
            )
            for segment in segments
        ]
        return render_speech_segments(normalized_segments)
    return _plain_speech_text_from_text(text, pronunciations)


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
    converted = re.sub(r"\*\*([^*]+)\*\*", r"\1", converted)
    converted = re.sub(r"\*([^*]+)\*", r"\1", converted)
    converted = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", converted)
    converted = re.sub(r"https?://\S+", "リンク", converted)
    converted = re.sub(
        r"\$([0-9]+)k\b",
        lambda match: f"{int(match.group(1)) * 1000}ドル",
        converted,
        flags=re.IGNORECASE,
    )
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


def _speech_lines_from_markdown_line(
    line: str, pronunciations: PronunciationPairs = ()
) -> list[str]:
    heading = re.match(r"^(#+)\s*(.+)$", line)
    if heading:
        level = len(heading.group(1))
        text = _heading_to_speech(heading.group(2), level)
    else:
        text = re.sub(r"^[-*]\s+", "", line)
    return _speech_lines_from_text(text, pronunciations)


def _speech_lines_from_text(text: str, pronunciations: PronunciationPairs = ()) -> list[str]:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = normalize_symbols_for_tts(text)
    text = normalize_for_tts(text, pronunciations)
    return _split_speech_line(text)


def _plain_speech_text_from_text(text: str, pronunciations: PronunciationPairs = ()) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or re.fullmatch(r"-{3,}", line):
            continue
        lines.extend(_speech_lines_from_markdown_line(line, pronunciations))
    return "\n".join(lines)


def _heading_to_speech(text: str, level: int) -> str:
    normalized = re.sub(r"^\d+\.\s*", "", text.strip())
    replacements = {
        "Daily AI Signal Radio": "エーアイシグナルラジオです。",
        "AI Signal Radio Deep Dive": "エーアイシグナルラジオ、深掘り版です。",
        "一言ニュース": "ここからは一言ニュースです。",
        "今日の深掘り候補": "今日の深掘り候補です。",
        "事実": "まず事実です。",
        "解釈": "次に意味合いです。",
        "試す価値": "試すなら、ここを見ます。",
        "未確認事項": "最後に、未確認の点です。",
    }
    if normalized in replacements:
        return replacements[normalized]
    if level == 1 and normalized:
        return f"{normalized}です。"
    return normalized


def _split_speech_line(text: str, max_chars: int = 64) -> list[str]:
    if not text:
        return []
    sentences = [unit.strip() for unit in re.split(r"(?<=[。！？])", text) if unit.strip()]
    if not sentences:
        sentences = [text]
    lines: list[str] = []
    for sentence in sentences:
        lines.extend(_split_long_speech_unit(sentence, max_chars=max_chars))
    return lines


def _split_long_speech_unit(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts = [part for part in re.split(r"(?<=、)", text) if part]
    if len(parts) <= 1:
        return [text]

    lines: list[str] = []
    current = ""
    for part in parts:
        if current and len(current) + len(part) > max_chars:
            lines.append(current.rstrip("、"))
            current = part
        else:
            current = f"{current}{part}"
    if current:
        lines.append(current.rstrip("、"))
    return lines


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
