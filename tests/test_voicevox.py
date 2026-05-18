from ai_signal_radio.tts.voicevox import (
    SpeechSegment,
    apply_pronunciations,
    load_pronunciation_profile,
    markdown_to_speech_segments,
    markdown_to_speech_text,
    normalize_for_tts,
    normalize_symbols_for_tts,
    parse_speech_segments,
    render_speech_segments,
    split_for_tts_text,
)


def test_markdown_to_speech_text_strips_markdown_for_tts() -> None:
    markdown = """# Daily AI Signal Radio

## 1. Topic

取得元は hacker-news-ai です。arXiv と OpenAI も扱います。

LLM and AI update.
"""

    text = markdown_to_speech_text(markdown)

    assert "# Daily" not in text
    assert "Daily エーアイ Signal Radio" in text
    assert "hacker-news-ai" in text
    assert "アーカイブ" in text
    assert "オープンエーアイ" in text
    assert "エルエルエム and エーアイ update." in text
    assert "1. Topic" not in text
    assert "Topic" in text


def test_split_for_tts_chunks_long_text() -> None:
    text = "これはテストです。" * 80

    chunks = split_for_tts_text(text, max_chars=80)

    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_split_for_tts_text_expects_plain_speech_text() -> None:
    chunks = split_for_tts_text("# 見出しです。", max_chars=80)

    assert chunks == ["# 見出しです。"]


def test_apply_pronunciations_accepts_context_specific_pairs() -> None:
    text = apply_pronunciations(
        "Hacker News discussed AWS Bedrock and VOICEVOX.",
        (
            ("Hacker News", "ハッカーニュース"),
            ("VOICEVOX", "ボイスボックス"),
        ),
    )

    assert "ハッカーニュース" in text
    assert "ボイスボックス" in text
    assert "AWS Bedrock" in text


def test_normalize_for_tts_applies_technical_defaults() -> None:
    text = normalize_for_tts(
        "AI, LLM, API, SDK, Vercel AI SDK, LangGraph, AWS Bedrock, SQLite."
    )

    assert "エーアイ" in text
    assert "エルエルエム" in text
    assert "エーピーアイ" in text
    assert "エスディーケー" in text
    assert "バーセル エーアイ エスディーケー" in text
    assert "ランググラフ" in text
    assert "エーダブリューエス ベッドロック" in text
    assert "エスキューライト" in text


def test_normalize_for_tts_lets_profile_override_defaults() -> None:
    text = normalize_for_tts("API and AI", (("API", "アプリケーションピーアイ"),))

    assert "アプリケーションピーアイ" in text
    assert "エーアイ" in text


def test_normalize_symbols_for_tts_removes_url_and_punctuation_noise() -> None:
    text = normalize_symbols_for_tts(
        '1. Torrix: LLM Observability,(no Postgres, no Redis) https://example.com?a=1'
    )

    assert text == "Torrix、LLM Observability、no Postgres、no Redis、リンク"


def test_markdown_to_speech_text_normalizes_dialogue_labels() -> None:
    markdown = "Host: AWS Bedrock (API) を確認します。\nAnalyst: CI/CD と QA も見ます。"

    text = markdown_to_speech_text(markdown)

    assert "ホスト、エーダブリューエス ベッドロック、エーピーアイ、を確認します。" in text
    assert "アナリスト、シーアイ シーディー と キューエー も見ます。" in text


def test_markdown_to_speech_segments_assigns_dialogue_speakers() -> None:
    markdown = """# Deep Dive

Host: AWS Bedrock を確認します。
Analyst: API の制限を見ます。
地の文です。
"""

    segments = markdown_to_speech_segments(
        markdown,
        default_speaker=3,
        role_speakers={"host": 3, "analyst": 8},
    )

    assert segments == [
        SpeechSegment(text="Deep Dive\nエーダブリューエス ベッドロック を確認します。", speaker=3),
        SpeechSegment(text="エーピーアイ の制限を見ます。", speaker=8),
        SpeechSegment(text="地の文です。", speaker=3),
    ]


def test_render_and_parse_speech_segments_roundtrip() -> None:
    segments = [
        SpeechSegment(text="ホストの本文です。", speaker=3),
        SpeechSegment(text="分析側の本文です。", speaker=8),
    ]

    rendered = render_speech_segments(segments)

    assert rendered == "[speaker=3]\nホストの本文です。\n\n[speaker=8]\n分析側の本文です。"
    assert parse_speech_segments(rendered) == segments


def test_parse_speech_segments_ignores_plain_text() -> None:
    assert parse_speech_segments("これは普通の読み上げテキストです。") == []


def test_load_pronunciation_profile_reads_optional_yaml(tmp_path) -> None:
    profile = tmp_path / "pronunciations.yml"
    profile.write_text(
        """
pronunciations:
  - term: "VOICEVOX"
    reading: "ボイスボックス"
  - ["Hacker News", "ハッカーニュース"]
""".strip(),
        encoding="utf-8",
    )

    pronunciations = load_pronunciation_profile(profile)

    assert pronunciations == (
        ("VOICEVOX", "ボイスボックス"),
        ("Hacker News", "ハッカーニュース"),
    )
