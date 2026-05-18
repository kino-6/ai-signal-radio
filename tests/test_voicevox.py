from ai_signal_radio.tts.voicevox import apply_pronunciations, markdown_to_speech_text, split_for_tts


def test_markdown_to_speech_text_strips_markdown_for_tts() -> None:
    markdown = """# Daily AI Signal Radio

## 1. Topic

取得元は hacker-news-ai です。arXiv と OpenAI も扱います。

LLM and AI update.
"""

    text = markdown_to_speech_text(markdown)

    assert "# Daily" not in text
    assert "Daily AI Signal Radio" in text
    assert "hacker-news-ai" in text
    assert "arXiv" in text
    assert "OpenAI" in text
    assert "LLM and AI update." in text


def test_split_for_tts_chunks_long_text() -> None:
    text = "これはテストです。" * 80

    chunks = split_for_tts(text, max_chars=80)

    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)


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
