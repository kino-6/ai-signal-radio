from pathlib import Path
from datetime import datetime, timezone

from ai_signal_radio import cli
from ai_signal_radio.collectors.base import BaseCollector, CollectionError
from ai_signal_radio.config import SourceConfig
from ai_signal_radio.models import NewsItem
from ai_signal_radio.storage import load_raw_items, save_raw_items


def test_tts_command_uses_config_and_pronunciation_profile(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "sources.yml"
    profile_path = tmp_path / "pronunciations.yml"
    script_path = tmp_path / "daily.md"
    output_path = tmp_path / "daily.wav"
    seen: dict[str, object] = {}

    config_path.write_text(
        f"""
tts:
  endpoint: "http://voicevox.local:50021"
  speaker: 3
  speed_scale: 1.3
  pitch_scale: 0.1
  intonation_scale: 1.2
  pronunciation_profile: "{profile_path}"
""".strip(),
        encoding="utf-8",
    )
    profile_path.write_text(
        """
pronunciations:
  - term: "VOICEVOX"
    reading: "ボイスボックス"
""".strip(),
        encoding="utf-8",
    )
    script_path.write_text("# Daily\n\nVOICEVOX で読み上げます。", encoding="utf-8")

    class FakeVoicevoxClient:
        def __init__(self, base_url: str) -> None:
            seen["base_url"] = base_url

        def healthcheck(self) -> bool:
            return True

        def synthesize_to_wav(
            self,
            text: str,
            output_path: Path,
            speaker: int = 3,
            speed_scale: float = 1.0,
            pitch_scale: float = 0.0,
            intonation_scale: float = 1.0,
        ) -> Path:
            seen["text"] = text
            seen["speaker"] = speaker
            seen["speed_scale"] = speed_scale
            seen["pitch_scale"] = pitch_scale
            seen["intonation_scale"] = intonation_scale
            output_path.write_bytes(b"RIFF")
            return output_path

    monkeypatch.setattr(cli, "VoicevoxClient", FakeVoicevoxClient)

    result = cli.tts_command(script_path, output_path, config_path=config_path)

    assert result == output_path
    assert seen["base_url"] == "http://voicevox.local:50021"
    assert seen["speaker"] == 3
    assert seen["speed_scale"] == 1.3
    assert seen["pitch_scale"] == 0.1
    assert seen["intonation_scale"] == 1.2
    assert "ボイスボックス" in str(seen["text"])


def test_tts_command_can_use_dialogue_speakers(tmp_path, monkeypatch) -> None:
    script_path = tmp_path / "deep-dive.md"
    output_path = tmp_path / "deep-dive.wav"
    seen: dict[str, object] = {}
    script_path.write_text(
        "Host: AWS Bedrock を確認します。\nAnalyst: API の制限を見ます。",
        encoding="utf-8",
    )

    class FakeVoicevoxClient:
        def __init__(self, base_url: str) -> None:
            seen["base_url"] = base_url

        def healthcheck(self) -> bool:
            return True

        def synthesize_segments_to_wav(
            self,
            segments,
            output_path: Path,
            speed_scale: float = 1.0,
            pitch_scale: float = 0.0,
            intonation_scale: float = 1.0,
        ) -> Path:
            seen["segments"] = segments
            seen["speed_scale"] = speed_scale
            output_path.write_bytes(b"RIFF")
            return output_path

    monkeypatch.setattr(cli, "VoicevoxClient", FakeVoicevoxClient)

    result = cli.tts_command(
        script_path,
        output_path,
        speaker=3,
        host_speaker=3,
        analyst_speaker=8,
        speed_scale=1.2,
    )

    assert result == output_path
    assert [segment.speaker for segment in seen["segments"]] == [3, 8]
    assert "エーダブリューエス ベッドロック" in seen["segments"][0].text
    assert "エーピーアイ" in seen["segments"][1].text
    assert seen["speed_scale"] == 1.2


def test_tts_script_command_writes_plain_speech_text(tmp_path) -> None:
    script_path = tmp_path / "daily.md"
    output_path = tmp_path / "daily.tts.txt"
    script_path.write_text("# Daily\n\nAI と OpenAI のニュースです。", encoding="utf-8")

    result = cli.tts_script_command(script_path, output_path)

    assert result == output_path
    text = output_path.read_text(encoding="utf-8")
    assert "# Daily" not in text
    assert "Daily" in text
    assert "エーアイ" in text
    assert "オープンエーアイ" in text


def test_tts_script_command_writes_dialogue_speaker_blocks(tmp_path) -> None:
    script_path = tmp_path / "deep-dive.md"
    output_path = tmp_path / "deep-dive.tts.txt"
    script_path.write_text(
        "Host: AWS Bedrock を確認します。\nAnalyst: API の制限を見ます。",
        encoding="utf-8",
    )

    result = cli.tts_script_command(
        script_path,
        output_path,
        speaker=3,
        host_speaker=3,
        analyst_speaker=8,
    )

    assert result == output_path
    text = output_path.read_text(encoding="utf-8")
    assert "[speaker=3]" in text
    assert "[speaker=8]" in text
    assert "エーダブリューエス ベッドロック" in text
    assert "エーピーアイ" in text


def test_tts_command_reads_segmented_tts_script(tmp_path, monkeypatch) -> None:
    script_path = tmp_path / "deep-dive.tts.txt"
    output_path = tmp_path / "deep-dive.wav"
    seen: dict[str, object] = {}
    script_path.write_text(
        "[speaker=3]\nホストの本文です。\n\n[speaker=8]\n分析側の本文です。",
        encoding="utf-8",
    )

    class FakeVoicevoxClient:
        def __init__(self, base_url: str) -> None:
            seen["base_url"] = base_url

        def healthcheck(self) -> bool:
            return True

        def synthesize_segments_to_wav(
            self,
            segments,
            output_path: Path,
            speed_scale: float = 1.0,
            pitch_scale: float = 0.0,
            intonation_scale: float = 1.0,
        ) -> Path:
            seen["segments"] = segments
            output_path.write_bytes(b"RIFF")
            return output_path

    monkeypatch.setattr(cli, "VoicevoxClient", FakeVoicevoxClient)

    result = cli.tts_command(script_path, output_path)

    assert result == output_path
    assert [segment.speaker for segment in seen["segments"]] == [3, 8]
    assert seen["segments"][0].text == "ホストの本文です。"
    assert seen["segments"][1].text == "分析側の本文です。"


def test_main_prints_friendly_tts_error(monkeypatch, tmp_path, capsys) -> None:
    script_path = tmp_path / "daily.md"
    script_path.write_text("# Daily", encoding="utf-8")

    def fail_tts_command(**kwargs) -> Path:
        raise RuntimeError("VOICEVOX engine に接続できません。")

    monkeypatch.setattr(cli, "tts_command", fail_tts_command)

    exit_code = cli.main(["tts", "--input", str(script_path)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "error: VOICEVOX engine に接続できません。" in captured.err


def test_build_collectors_passes_timeout_and_rate_limit() -> None:
    collectors = cli.build_collectors(
        (
            SourceConfig(
                name="hn",
                type="hackernews",
                params={
                    "query": "AI",
                    "timeout_seconds": 9,
                    "rate_limit_seconds": 0.25,
                },
            ),
        )
    )

    assert collectors[0].timeout_seconds == 9
    assert collectors[0].rate_limit_seconds == 0.25


def test_rebuild_command_reprocesses_existing_raw_json(tmp_path) -> None:
    data_dir = tmp_path / "data"
    raw_dir = tmp_path / "raw"
    item = NewsItem(
        source="demo",
        source_type="demo",
        title="Rebuild AI item",
        url="https://example.com/rebuild",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        summary="再処理できるニュースです。",
        tags=("ai",),
    )
    raw_path = save_raw_items([item], raw_dir)

    result = cli.rebuild_command(raw_path, data_dir=data_dir, limit=5)

    assert result.raw_path == str(raw_path)
    assert result.processed_path == str(data_dir / "processed" / "latest.json")
    assert result.selected_count == 1
    assert Path(result.processed_path).exists()
    assert Path(result.script_path).exists()
    assert Path(result.wiki_path).exists()
    assert (data_dir / "wiki" / "topics" / "ai.md").exists()


def test_run_command_saves_processed_ranked_items(tmp_path) -> None:
    result = cli.demo_command(data_dir=tmp_path / "data", limit=2)

    assert result.processed_path
    processed = load_raw_items(Path(result.processed_path))

    assert len(processed) == 2
    assert processed[0].score >= processed[1].score
    assert "score_breakdown" in processed[0].metadata
    assert "dedupe" in processed[0].metadata
    assert "topic_cluster" in processed[0].metadata


def test_write_pipeline_outputs_uses_single_run_timestamp(tmp_path) -> None:
    run_at = datetime(2026, 5, 18, 1, 2, 3, tzinfo=timezone.utc)
    run_id = "20260518T010203000000Z"
    item = NewsItem(
        source="demo",
        source_type="demo",
        title="Timestamped AI item",
        url="https://example.com/timestamped",
        published_at=datetime(2026, 5, 17, tzinfo=timezone.utc),
        summary="時刻の揃った出力を確認します。",
        tags=("ai",),
    )

    wiki_path, script_path = cli._write_pipeline_outputs(
        [item],
        tmp_path / "data",
        run_id=run_id,
        run_at=run_at,
    )

    assert wiki_path == tmp_path / "data" / "wiki" / "2026-05-18" / run_id
    assert script_path.name == f"2026-05-18-{run_id}-daily.md"


def test_collect_all_with_report_records_failures() -> None:
    class FailingCollector(BaseCollector):
        def collect(self, limit: int = 20) -> list[NewsItem]:
            raise CollectionError("HTTP 429")

    items, failures = cli.collect_all_with_report([FailingCollector("arxiv-ai")], limit=5)

    assert items == []
    assert failures == [
        {
            "source": "arxiv-ai",
            "error_type": "CollectionError",
            "message": "HTTP 429",
        }
    ]
