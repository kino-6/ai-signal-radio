import json
from urllib.request import Request

from ai_signal_radio.tts.speech_editor import OllamaSpeechEditor


def test_ollama_speech_editor_uses_injected_transport() -> None:
    seen: dict[str, object] = {}

    def fake_transport(request: Request, timeout_seconds: int) -> bytes:
        seen["url"] = request.full_url
        seen["timeout"] = timeout_seconds
        return json.dumps({"response": "短く聞きやすい本文です。"}).encode("utf-8")

    editor = OllamaSpeechEditor(
        model="gemma4:latest",
        base_url="http://127.0.0.1:11434",
        transport=fake_transport,
    )

    text = editor.edit("これは少し長い本文です。")

    assert text == "短く聞きやすい本文です。"
    assert seen["url"] == "http://127.0.0.1:11434/api/generate"


def test_ollama_speech_editor_preserves_speaker_blocks() -> None:
    def fake_transport(request: Request, timeout_seconds: int) -> bytes:
        body = json.loads(request.data.decode("utf-8"))  # type: ignore[union-attr]
        prompt = body["prompt"]
        if "ホストの本文" in prompt:
            response = "ホストの編集済み本文です。"
        else:
            response = "分析側の編集済み本文です。"
        return json.dumps({"response": response}).encode("utf-8")

    editor = OllamaSpeechEditor(transport=fake_transport)

    text = editor.edit("[speaker=3]\nホストの本文です。\n\n[speaker=8]\n分析側の本文です。")

    assert text == (
        "[speaker=3]\nホストの編集済み本文です。\n\n"
        "[speaker=8]\n分析側の編集済み本文です。"
    )


def test_ollama_speech_editor_falls_back_on_bad_response() -> None:
    def fake_transport(request: Request, timeout_seconds: int) -> bytes:
        return b"not json"

    editor = OllamaSpeechEditor(transport=fake_transport)

    assert editor.edit("元の本文です。") == "元の本文です。"
