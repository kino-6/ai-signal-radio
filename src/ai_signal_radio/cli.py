"""Command-line interface for ai-signal-radio."""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from ai_signal_radio.collectors.arxiv import ArxivCollector
from ai_signal_radio.collectors.base import BaseCollector, CollectionError, DemoCollector
from ai_signal_radio.collectors.hackernews import HackerNewsCollector
from ai_signal_radio.collectors.rss import RssCollector
from ai_signal_radio.config import (
    AppConfig,
    EditorialSkill,
    RankerConfig,
    SourceConfig,
    TopicProfile,
    load_config,
    load_editorial_skill,
    load_topic_profile,
)
from ai_signal_radio.editorial import EditorialReviewer, OllamaEditorialReviewer
from ai_signal_radio.docs_preview import DocsPreviewResult, build_mkdocs_preview
from ai_signal_radio.models import EditorialReview, NewsItem, PipelineResult
from ai_signal_radio.processors.dedupe import DedupeResult, dedupe_items, dedupe_items_with_report
from ai_signal_radio.processors.ranker import rank_items
from ai_signal_radio.processors.script_writer import write_script
from ai_signal_radio.profiles import RunProfile, load_run_profile, write_run_profile
from ai_signal_radio.processors.wiki_writer import (
    Summarizer,
    load_wiki_notes,
    write_topic_pages,
    write_wiki_notes,
)
from ai_signal_radio.storage import (
    date_slug,
    ensure_data_dirs,
    load_raw_items,
    save_dedupe_report,
    save_processed_items,
    save_run_metadata,
    save_raw_items,
    timestamp_slug,
)
from ai_signal_radio.summarizers.ollama import OllamaSummarizer
from ai_signal_radio.tts.voicevox import (
    PronunciationPairs,
    VoicevoxClient,
    load_pronunciation_profile,
    markdown_to_speech_segments,
    markdown_to_speech_text,
    normalize_speech_text,
    parse_speech_segments,
    render_speech_segments,
)
from ai_signal_radio.tts.speech_editor import OllamaSpeechEditor


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(raw_argv)

    if args.command == "collect":
        path = collect_command(
            config_path=args.config,
            limit=args.limit,
            data_dir=args.data_dir,
            source_filter=tuple(args.source),
            dry_run=args.dry_run,
        )
        if path:
            print(f"Collected raw items: {path}")
        return 0
    if args.command == "wiki":
        paths = wiki_command(
            input_path=args.input,
            output_dir=args.output,
            summarizer_name=args.summarizer,
            ollama_model=args.ollama_model,
            ollama_url=args.ollama_url,
            topic_path=args.topic,
        )
        print(f"Wrote wiki notes: {len(paths)}")
        for path in paths:
            print(path)
        return 0
    if args.command == "script":
        path = script_command(
            input_path=args.input,
            output_path=args.output,
            style=args.style,
            topic_path=args.topic,
        )
        print(f"Wrote script: {path}")
        return 0
    if args.command == "docs":
        result = docs_command(
            wiki_dir=args.wiki,
            script_path=args.script,
            audio_dir=args.audio_dir,
            output_dir=args.output,
            processed_path=args.processed,
        )
        print(f"Wrote MkDocs preview: {result.index_path}")
        print(f"Copied wiki notes: {result.copied_note_count}")
        print(f"Copied topic pages: {result.copied_topic_count}")
        print(f"Copied audio files: {result.copied_audio_count}")
        if result.radio_path:
            print(f"Copied radio script: {result.radio_path}")
        return 0
    if args.command == "profile":
        if args.profile_command == "export":
            path = profile_export_command(
                output_path=args.output,
                name=args.name,
                config_path=args.config,
                data_dir=args.data_dir,
                topic_path=args.topic,
                editorial_skill_path=args.editorial_skill,
                limit=args.limit,
                collect_limit=args.collect_limit,
                source=tuple(args.source),
                summarizer_name=args.summarizer,
                ollama_model=args.ollama_model,
                ollama_url=args.ollama_url,
                script_style=args.script_style,
                editorial_model=args.editorial_model,
                editorial_url=args.editorial_url,
            )
            print(f"Wrote run profile: {path}")
            return 0
        if args.profile_command == "import":
            try:
                profile_doc = profile_import_command(args.input, strict=args.strict)
            except ValueError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
            for warning in profile_doc.warnings:
                print(f"warning: {warning}", file=sys.stderr)
            print(f"Imported run profile: {profile_doc.profile.name}")
            print(f"Run with: ai-signal run --profile {args.input}")
            return 0
        parser.print_help()
        return 1
    if args.command == "tts":
        try:
            path = tts_command(
                input_path=args.input,
                output_path=args.output,
                config_path=args.config,
                speaker=args.speaker,
                host_speaker=args.host_speaker,
                analyst_speaker=args.analyst_speaker,
                speed_scale=args.speed,
                pitch_scale=args.pitch,
                intonation_scale=args.intonation,
                voicevox_url=args.voicevox_url,
                pronunciation_profile=args.pronunciation_profile,
            )
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"Wrote audio: {path}")
        return 0
    if args.command == "tts-script":
        try:
            path = tts_script_command(
                input_path=args.input,
                output_path=args.output,
                config_path=args.config,
                speaker=args.speaker,
                host_speaker=args.host_speaker,
                analyst_speaker=args.analyst_speaker,
                pronunciation_profile=args.pronunciation_profile,
                speech_editor=args.speech_editor,
                speech_editor_model=args.speech_editor_model,
                speech_editor_url=args.speech_editor_url,
            )
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"Wrote TTS script: {path}")
        return 0
    if args.command == "run":
        try:
            run_args = _resolve_run_profile_args(args, raw_argv)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        result = run_command(**run_args)
        _print_result(result)
        return 0
    if args.command == "rebuild":
        result = rebuild_command(
            input_path=args.input,
            data_dir=args.data_dir,
            limit=args.limit,
            summarizer_name=args.summarizer,
            ollama_model=args.ollama_model,
            ollama_url=args.ollama_url,
            script_style=args.script_style,
            topic_path=args.topic,
            editorial_skill_path=args.editorial_skill,
            editorial_model=args.editorial_model,
            editorial_url=args.editorial_url,
        )
        _print_result(result)
        return 0
    if args.command == "demo":
        result = demo_command(data_dir=args.data_dir, limit=args.limit, topic_path=args.topic)
        _print_result(result)
        return 0

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-signal",
        description="Collect AI news and generate local-first wiki notes and radio scripts.",
    )
    subparsers = parser.add_subparsers(dest="command")

    collect = subparsers.add_parser("collect", help="Collect raw news items into data/raw/latest.json.")
    collect.add_argument("--config", type=Path, default=Path("config/sources.example.yml"))
    collect.add_argument("--limit", type=int, default=20)
    collect.add_argument("--data-dir", type=Path, default=Path("data"))
    collect.add_argument(
        "--source",
        action="append",
        default=[],
        help="Run only matching source names or source types. Can be passed multiple times.",
    )
    collect.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview collected titles without writing data/raw/latest.json.",
    )

    wiki = subparsers.add_parser("wiki", help="Convert raw JSON items into Markdown wiki notes.")
    wiki.add_argument("--input", type=Path, required=True)
    wiki.add_argument("--output", type=Path, required=True)
    wiki.add_argument("--topic", type=Path, default=None, help="Optional topic profile YAML.")
    add_summarizer_args(wiki)

    script = subparsers.add_parser("script", help="Generate a radio-style Markdown script.")
    script.add_argument("--input", type=Path, required=True)
    script.add_argument("--output", type=Path, required=True)
    script.add_argument("--topic", type=Path, default=None, help="Optional topic profile YAML.")
    script.add_argument(
        "--style",
        choices=("short", "standard", "detailed", "briefing", "dialogue"),
        default="standard",
        help="Control script length and detail.",
    )

    docs = subparsers.add_parser("docs", help="Generate ignored MkDocs preview pages.")
    docs.add_argument("--wiki", type=Path, default=Path("data/wiki"))
    docs.add_argument("--script", type=Path, default=Path("data/scripts/daily.md"))
    docs.add_argument("--audio-dir", type=Path, default=Path("data/audio"))
    docs.add_argument("--processed", type=Path, default=Path("data/processed/latest.json"))
    docs.add_argument("--output", type=Path, default=Path("docs/generated"))

    profile = subparsers.add_parser("profile", help="Import and export reusable run profiles.")
    profile_subparsers = profile.add_subparsers(dest="profile_command")
    profile_export = profile_subparsers.add_parser(
        "export",
        help="Write a JSON run profile from CLI options.",
    )
    profile_export.add_argument("--output", type=Path, required=True)
    profile_export.add_argument("--name", required=True)
    profile_export.add_argument("--config", type=Path, default=Path("config/sources.example.yml"))
    profile_export.add_argument("--data-dir", type=Path, default=Path("data"))
    profile_export.add_argument("--limit", type=int, default=20)
    profile_export.add_argument(
        "--collect-limit",
        type=int,
        default=None,
        help="Number of items to collect per source before dedupe/ranking.",
    )
    profile_export.add_argument("--topic", type=Path, default=None)
    profile_export.add_argument(
        "--source",
        action="append",
        default=[],
        help="Source names or source types to store in the profile.",
    )
    add_summarizer_args(profile_export)
    add_editorial_args(profile_export)
    profile_export.add_argument(
        "--script-style",
        choices=("short", "standard", "detailed", "briefing", "dialogue"),
        default="standard",
        help="Control generated radio script length and detail.",
    )

    profile_import = profile_subparsers.add_parser(
        "import",
        help="Validate a JSON run profile before using it with run --profile.",
    )
    profile_import.add_argument("--input", type=Path, required=True)
    profile_import.add_argument(
        "--strict",
        action="store_true",
        help="Fail if the profile contains unknown keys.",
    )

    tts = subparsers.add_parser("tts", help="Synthesize a Markdown script with local VOICEVOX.")
    tts.add_argument("--config", type=Path, default=Path("config/sources.example.yml"))
    tts.add_argument("--input", type=Path, required=True)
    tts.add_argument("--output", type=Path, default=Path("data/audio/daily.wav"))
    tts.add_argument("--speaker", type=int, default=None, help="VOICEVOX speaker ID. 3 is Zundamon.")
    tts.add_argument(
        "--host-speaker",
        type=int,
        default=None,
        help="Optional VOICEVOX speaker ID for dialogue lines starting with Host:",
    )
    tts.add_argument(
        "--analyst-speaker",
        type=int,
        default=None,
        help="Optional VOICEVOX speaker ID for dialogue lines starting with Analyst:",
    )
    tts.add_argument("--speed", type=float, default=None, help="VOICEVOX speedScale.")
    tts.add_argument("--pitch", type=float, default=None, help="VOICEVOX pitchScale.")
    tts.add_argument("--intonation", type=float, default=None, help="VOICEVOX intonationScale.")
    tts.add_argument("--voicevox-url", default=None)
    tts.add_argument(
        "--pronunciation-profile",
        type=Path,
        default=None,
        help="Optional YAML profile for context-specific pronunciation replacements.",
    )

    tts_script = subparsers.add_parser(
        "tts-script",
        help="Write normalized TTS text from a Markdown radio script.",
    )
    tts_script.add_argument("--config", type=Path, default=Path("config/sources.example.yml"))
    tts_script.add_argument("--input", type=Path, required=True)
    tts_script.add_argument("--output", type=Path, default=Path("data/scripts/daily.tts.txt"))
    tts_script.add_argument("--speaker", type=int, default=None, help="Default VOICEVOX speaker ID.")
    tts_script.add_argument(
        "--host-speaker",
        type=int,
        default=None,
        help="Optional VOICEVOX speaker ID for dialogue lines starting with Host:",
    )
    tts_script.add_argument(
        "--analyst-speaker",
        type=int,
        default=None,
        help="Optional VOICEVOX speaker ID for dialogue lines starting with Analyst:",
    )
    tts_script.add_argument(
        "--pronunciation-profile",
        type=Path,
        default=None,
        help="Optional YAML profile for context-specific pronunciation replacements.",
    )
    tts_script.add_argument(
        "--speech-editor",
        choices=("none", "ollama"),
        default="none",
        help="Optionally rewrite TTS text with a local speech editor pass.",
    )
    tts_script.add_argument(
        "--speech-editor-model",
        default="gemma4:latest",
        help="Ollama model for --speech-editor ollama.",
    )
    tts_script.add_argument(
        "--speech-editor-url",
        default="http://127.0.0.1:11434",
        help="Ollama base URL for --speech-editor ollama.",
    )

    demo = subparsers.add_parser("demo", help="Run a fully local sample pipeline.")
    demo.add_argument("--data-dir", type=Path, default=Path("data"))
    demo.add_argument("--limit", type=int, default=20)
    demo.add_argument("--topic", type=Path, default=None, help="Optional topic profile YAML.")

    run = subparsers.add_parser("run", help="Run collect, wiki, and script generation.")
    run.add_argument("--profile", type=Path, default=None, help="Import reusable run settings JSON.")
    run.add_argument("--config", type=Path, default=Path("config/sources.example.yml"))
    run.add_argument("--data-dir", type=Path, default=Path("data"))
    run.add_argument("--limit", type=int, default=20, help="Number of final items to select.")
    run.add_argument(
        "--collect-limit",
        type=int,
        default=None,
        help="Number of items to collect per source before dedupe/ranking. Defaults to --limit.",
    )
    run.add_argument("--topic", type=Path, default=None, help="Optional topic profile YAML.")
    run.add_argument(
        "--source",
        action="append",
        default=[],
        help="Run only matching source names or source types. Can be passed multiple times.",
    )
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="Collect and rank items, then print a preview without writing files.",
    )
    add_summarizer_args(run)
    add_editorial_args(run)
    run.add_argument(
        "--script-style",
        choices=("short", "standard", "detailed", "briefing", "dialogue"),
        default="standard",
        help="Control generated radio script length and detail.",
    )

    rebuild = subparsers.add_parser(
        "rebuild",
        help="Reprocess an existing raw JSON file into wiki notes and a radio script.",
    )
    rebuild.add_argument("--input", type=Path, default=Path("data/raw/latest.json"))
    rebuild.add_argument("--data-dir", type=Path, default=Path("data"))
    rebuild.add_argument("--limit", type=int, default=20)
    rebuild.add_argument("--topic", type=Path, default=None, help="Optional topic profile YAML.")
    add_summarizer_args(rebuild)
    add_editorial_args(rebuild)
    rebuild.add_argument(
        "--script-style",
        choices=("short", "standard", "detailed", "briefing", "dialogue"),
        default="standard",
        help="Control generated radio script length and detail.",
    )
    return parser


def add_summarizer_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--summarizer",
        choices=("placeholder", "ollama"),
        default="placeholder",
        help="Use deterministic placeholders or explicit local Ollama summarization.",
    )
    parser.add_argument(
        "--ollama-model",
        default="gemma4:latest",
        help="Ollama model name used when --summarizer ollama is selected.",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://127.0.0.1:11434",
        help="Ollama base URL used when --summarizer ollama is selected.",
    )


def add_editorial_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--editorial-skill",
        type=Path,
        default=None,
        help="Optional local editorial skill YAML for topic-specific daily selection.",
    )
    parser.add_argument(
        "--editorial-model",
        default="gemma4:latest",
        help="Ollama model name used when --editorial-skill is selected.",
    )
    parser.add_argument(
        "--editorial-url",
        default="http://127.0.0.1:11434",
        help="Ollama base URL used when --editorial-skill is selected.",
    )


def profile_export_command(
    output_path: Path,
    name: str,
    config_path: Path = Path("config/sources.example.yml"),
    data_dir: Path = Path("data"),
    topic_path: Path | None = None,
    editorial_skill_path: Path | None = None,
    limit: int = 20,
    collect_limit: int | None = None,
    source: tuple[str, ...] = (),
    summarizer_name: str = "placeholder",
    ollama_model: str = "gemma4:latest",
    ollama_url: str = "http://127.0.0.1:11434",
    script_style: str = "standard",
    editorial_model: str = "gemma4:latest",
    editorial_url: str = "http://127.0.0.1:11434",
) -> Path:
    profile = RunProfile(
        name=name,
        config=str(config_path),
        data_dir=str(data_dir),
        topic=str(topic_path) if topic_path else None,
        editorial_skill=str(editorial_skill_path) if editorial_skill_path else None,
        limit=limit,
        collect_limit=collect_limit,
        source=source,
        summarizer=summarizer_name,
        ollama_model=ollama_model,
        ollama_url=ollama_url,
        script_style=script_style,
        editorial_model=editorial_model,
        editorial_url=editorial_url,
    )
    return write_run_profile(output_path, profile)


def profile_import_command(input_path: Path, strict: bool = False):
    return load_run_profile(input_path, strict=strict)


def _resolve_run_profile_args(args: argparse.Namespace, argv: list[str]) -> dict[str, object]:
    profile: RunProfile | None = None
    if args.profile is not None:
        profile_doc = load_run_profile(args.profile)
        for warning in profile_doc.warnings:
            print(f"warning: {warning}", file=sys.stderr)
        profile = profile_doc.profile
        print(f"Using run profile: {profile.name}")

    return {
        "config_path": Path(
            _profile_value(args.config, profile.config if profile else None, argv, "--config")
        ),
        "data_dir": Path(
            _profile_value(args.data_dir, profile.data_dir if profile else None, argv, "--data-dir")
        ),
        "limit": int(_profile_value(args.limit, profile.limit if profile else None, argv, "--limit")),
        "collect_limit": _profile_value(
            args.collect_limit,
            profile.collect_limit if profile else None,
            argv,
            "--collect-limit",
        ),
        "source_filter": tuple(
            _profile_source_value(args.source, profile.source if profile else (), argv)
        ),
        "dry_run": args.dry_run,
        "summarizer_name": _profile_value(
            args.summarizer,
            profile.summarizer if profile else None,
            argv,
            "--summarizer",
        ),
        "ollama_model": _profile_value(
            args.ollama_model,
            profile.ollama_model if profile else None,
            argv,
            "--ollama-model",
        ),
        "ollama_url": _profile_value(
            args.ollama_url,
            profile.ollama_url if profile else None,
            argv,
            "--ollama-url",
        ),
        "script_style": _profile_value(
            args.script_style,
            profile.script_style if profile else None,
            argv,
            "--script-style",
        ),
        "topic_path": _profile_optional_path(args.topic, profile.topic if profile else None, argv, "--topic"),
        "editorial_skill_path": _profile_optional_path(
            args.editorial_skill,
            profile.editorial_skill if profile else None,
            argv,
            "--editorial-skill",
        ),
        "editorial_model": _profile_value(
            args.editorial_model,
            profile.editorial_model if profile else None,
            argv,
            "--editorial-model",
        ),
        "editorial_url": _profile_value(
            args.editorial_url,
            profile.editorial_url if profile else None,
            argv,
            "--editorial-url",
        ),
    }


def _profile_value(current: object, profile_value: object | None, argv: list[str], option: str):
    if profile_value is not None and not _argv_has_option(argv, option):
        return profile_value
    return current


def _profile_optional_path(
    current: Path | None,
    profile_value: str | None,
    argv: list[str],
    option: str,
) -> Path | None:
    value = _profile_value(current, profile_value, argv, option)
    return Path(value) if value else None


def _profile_source_value(
    current: list[str],
    profile_value: tuple[str, ...],
    argv: list[str],
) -> tuple[str, ...] | list[str]:
    if profile_value and not _argv_has_option(argv, "--source"):
        return profile_value
    return current


def _argv_has_option(argv: list[str], option: str) -> bool:
    return any(value == option or value.startswith(f"{option}=") for value in argv)


def collect_command(
    config_path: Path,
    limit: int = 20,
    data_dir: Path = Path("data"),
    source_filter: tuple[str, ...] = (),
    dry_run: bool = False,
) -> Path | None:
    run_at = datetime.now(timezone.utc)
    config = load_config(config_path) if config_path.exists() else AppConfig()
    items = collect_all(build_collectors(config.sources, source_filter=source_filter), limit=limit)
    if dry_run:
        dedupe_result = dedupe_items_with_report(items)
        ranked = rank_items(
            dedupe_result.selected_items,
            limit=limit,
            config=config.ranker,
            topic_profile=config.topic,
        )
        _print_preview(items, ranked)
        return None
    ensure_data_dirs(data_dir)
    run_id = timestamp_slug(run_at)
    return save_raw_items(items, data_dir, now=run_at, run_id=run_id)


def wiki_command(
    input_path: Path,
    output_dir: Path,
    summarizer_name: str = "placeholder",
    ollama_model: str = "gemma4:latest",
    ollama_url: str = "http://127.0.0.1:11434",
    topic_path: Path | None = None,
) -> list[Path]:
    run_at = datetime.now(timezone.utc)
    run_id = timestamp_slug(run_at)
    items = load_raw_items(input_path)
    topic_profile = _load_topic_profile(topic_path)
    ranked = (
        items
        if _looks_processed(items)
        else rank_items(dedupe_items(items), limit=len(items) or 20, topic_profile=topic_profile)
    )
    summarizer = build_summarizer(summarizer_name, ollama_model, ollama_url, topic_profile)
    paths = write_wiki_notes(
        ranked,
        output_dir,
        summarizer=summarizer,
        clean_day=True,
        now=run_at,
        run_id=run_id,
        topic_profile=topic_profile,
    )
    write_topic_pages([load_wiki_notes(path)[0] for path in paths], output_dir / "topics")
    return paths


def script_command(
    input_path: Path,
    output_path: Path,
    style: str = "standard",
    topic_path: Path | None = None,
) -> Path:
    notes = load_wiki_notes(input_path)
    notes = sorted(notes, key=lambda note: note.score, reverse=True)
    return write_script(notes, output_path, style=style, topic_profile=_load_topic_profile(topic_path))


def docs_command(
    wiki_dir: Path = Path("data/wiki"),
    script_path: Path = Path("data/scripts/daily.md"),
    audio_dir: Path = Path("data/audio"),
    output_dir: Path = Path("docs/generated"),
    processed_path: Path | None = Path("data/processed/latest.json"),
) -> DocsPreviewResult:
    return build_mkdocs_preview(
        wiki_dir=wiki_dir,
        script_path=script_path,
        audio_dir=audio_dir,
        output_dir=output_dir,
        processed_path=processed_path,
    )


def tts_script_command(
    input_path: Path,
    output_path: Path,
    config_path: Path = Path("config/sources.example.yml"),
    speaker: int | None = None,
    host_speaker: int | None = None,
    analyst_speaker: int | None = None,
    pronunciation_profile: Path | None = None,
    speech_editor: str = "none",
    speech_editor_model: str = "gemma4:latest",
    speech_editor_url: str = "http://127.0.0.1:11434",
) -> Path:
    config = load_config(config_path) if config_path.exists() else AppConfig()
    speaker = speaker if speaker is not None else config.tts.speaker
    profile_path = _resolve_pronunciation_profile(
        config=config,
        config_path=config_path,
        pronunciation_profile=pronunciation_profile,
    )
    pronunciations = _load_pronunciations_or_raise(profile_path)
    markdown = input_path.read_text(encoding="utf-8")
    role_speakers = _role_speakers(host_speaker=host_speaker, analyst_speaker=analyst_speaker)

    if role_speakers:
        speech_text = render_speech_segments(
            markdown_to_speech_segments(
                markdown,
                default_speaker=speaker,
                role_speakers=role_speakers,
                pronunciations=pronunciations,
            )
        )
    else:
        speech_text = markdown_to_speech_text(markdown, pronunciations=pronunciations)

    if speech_editor == "ollama":
        editor = OllamaSpeechEditor(model=speech_editor_model, base_url=speech_editor_url)
        speech_text = normalize_speech_text(editor.edit(speech_text), pronunciations=pronunciations)
    elif speech_editor != "none":
        raise RuntimeError(f"unsupported speech editor: {speech_editor}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"{speech_text.rstrip()}\n", encoding="utf-8")
    return output_path


def tts_command(
    input_path: Path,
    output_path: Path,
    config_path: Path = Path("config/sources.example.yml"),
    speaker: int | None = None,
    host_speaker: int | None = None,
    analyst_speaker: int | None = None,
    speed_scale: float | None = None,
    pitch_scale: float | None = None,
    intonation_scale: float | None = None,
    voicevox_url: str | None = None,
    pronunciation_profile: Path | None = None,
) -> Path:
    config = load_config(config_path) if config_path.exists() else AppConfig()
    tts_config = config.tts
    voicevox_url = voicevox_url or tts_config.endpoint
    speaker = speaker if speaker is not None else tts_config.speaker
    speed_scale = speed_scale if speed_scale is not None else tts_config.speed_scale
    pitch_scale = pitch_scale if pitch_scale is not None else tts_config.pitch_scale
    intonation_scale = (
        intonation_scale if intonation_scale is not None else tts_config.intonation_scale
    )
    profile_path = _resolve_pronunciation_profile(
        config=config,
        config_path=config_path,
        pronunciation_profile=pronunciation_profile,
    )

    client = VoicevoxClient(base_url=voicevox_url)
    if not client.healthcheck():
        raise RuntimeError(
            "VOICEVOX engine に接続できません。"
            f"起動しているか確認してください: {voicevox_url} "
            "VOICEVOX アプリを起動してから `uv run ai-signal tts ...` を再実行します。"
        )
    markdown = input_path.read_text(encoding="utf-8")
    pronunciations = _load_pronunciations_or_raise(profile_path)
    parsed_segments = parse_speech_segments(markdown)
    if parsed_segments:
        return client.synthesize_segments_to_wav(
            parsed_segments,
            output_path,
            speed_scale=speed_scale,
            pitch_scale=pitch_scale,
            intonation_scale=intonation_scale,
        )
    role_speakers = _role_speakers(host_speaker=host_speaker, analyst_speaker=analyst_speaker)
    if role_speakers:
        speech_segments = markdown_to_speech_segments(
            markdown,
            default_speaker=speaker,
            role_speakers=role_speakers,
            pronunciations=pronunciations,
        )
        return client.synthesize_segments_to_wav(
            speech_segments,
            output_path,
            speed_scale=speed_scale,
            pitch_scale=pitch_scale,
            intonation_scale=intonation_scale,
        )
    speech_text = markdown_to_speech_text(markdown, pronunciations=pronunciations)
    return client.synthesize_to_wav(
        speech_text,
        output_path,
        speaker=speaker,
        speed_scale=speed_scale,
        pitch_scale=pitch_scale,
        intonation_scale=intonation_scale,
    )


def _resolve_pronunciation_profile(
    config: AppConfig,
    config_path: Path,
    pronunciation_profile: Path | None,
) -> Path | None:
    profile_path = pronunciation_profile
    if profile_path is None and config.tts.pronunciation_profile:
        profile_path = Path(config.tts.pronunciation_profile)
        if not profile_path.is_absolute() and not profile_path.exists():
            profile_path = config_path.parent / profile_path
    return profile_path


def _load_pronunciations_or_raise(profile_path: Path | None) -> PronunciationPairs:
    try:
        return load_pronunciation_profile(profile_path)
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"pronunciation profile を読み込めません: {profile_path}: {exc}") from exc


def _resolve_topic_profile(config: AppConfig, topic_path: Path | None) -> TopicProfile:
    if topic_path is not None:
        return load_topic_profile(topic_path)
    return config.topic


def _load_topic_profile(topic_path: Path | None) -> TopicProfile:
    if topic_path is None:
        return TopicProfile()
    return load_topic_profile(topic_path)


def _load_editorial_skill(editorial_skill_path: Path | None) -> EditorialSkill | None:
    if editorial_skill_path is None:
        return None
    return load_editorial_skill(editorial_skill_path)


def _role_speakers(host_speaker: int | None, analyst_speaker: int | None) -> dict[str, int]:
    return {
        role: speaker_id
        for role, speaker_id in {
            "host": host_speaker,
            "analyst": analyst_speaker,
        }.items()
        if speaker_id is not None
    }


def run_command(
    config_path: Path,
    data_dir: Path = Path("data"),
    limit: int = 20,
    collect_limit: int | None = None,
    source_filter: tuple[str, ...] = (),
    dry_run: bool = False,
    summarizer_name: str = "placeholder",
    ollama_model: str = "gemma4:latest",
    ollama_url: str = "http://127.0.0.1:11434",
    script_style: str = "standard",
    topic_path: Path | None = None,
    editorial_skill_path: Path | None = None,
    editorial_model: str = "gemma4:latest",
    editorial_url: str = "http://127.0.0.1:11434",
) -> PipelineResult:
    run_at = datetime.now(timezone.utc)
    config = load_config(config_path) if config_path.exists() else AppConfig()
    topic_profile = _resolve_topic_profile(config, topic_path)
    editorial_skill = _load_editorial_skill(editorial_skill_path)
    editorial_reviewer = build_editorial_reviewer(
        editorial_skill,
        editorial_model,
        editorial_url,
        topic_profile,
    )
    collection_limit = collect_limit if collect_limit is not None else limit
    collected, collection_failures = collect_all_with_report(
        build_collectors(config.sources, source_filter=source_filter),
        limit=collection_limit,
    )
    dedupe_result, ranked, processed = _process_items(
        collected,
        limit=limit,
        ranker_config=config.ranker,
        topic_profile=topic_profile,
        editorial_reviewer=editorial_reviewer,
    )

    if dry_run:
        _print_preview(collected, ranked)
        return PipelineResult(
            collected_count=len(collected),
            deduped_count=len(dedupe_result.selected_items),
            selected_count=len(ranked),
            raw_path="dry-run: not written",
            processed_path="dry-run: not written",
            wiki_path="dry-run: not written",
            script_path="dry-run: not written",
        )

    ensure_data_dirs(data_dir)
    run_id = timestamp_slug(run_at)
    raw_path = save_raw_items(collected, data_dir, now=run_at, run_id=run_id)
    processed_path = save_processed_items(processed, data_dir, run_id=run_id, now=run_at)
    dedupe_report_path = save_dedupe_report(dedupe_result, data_dir, run_id, now=run_at)
    run_metadata_path = save_run_metadata(
        _run_metadata(
            collected=collected,
            processed=processed,
            collection_failures=collection_failures,
            run_id=run_id,
            run_at=run_at,
            collect_limit=collection_limit,
            selection_limit=limit,
            topic_profile=topic_profile,
            editorial_skill=editorial_skill,
        ),
        data_dir,
        run_id,
        now=run_at,
    )
    summarizer = build_summarizer(summarizer_name, ollama_model, ollama_url, topic_profile)
    wiki_path, script_path = _write_pipeline_outputs(
        ranked,
        data_dir,
        run_id=run_id,
        run_at=run_at,
        summarizer=summarizer,
        script_style=script_style,
        topic_profile=topic_profile,
    )
    return PipelineResult(
        collected_count=len(collected),
        deduped_count=len(dedupe_result.selected_items),
        selected_count=len(ranked),
        raw_path=str(raw_path),
        wiki_path=str(wiki_path),
        script_path=str(script_path),
        processed_path=str(processed_path),
        dedupe_report_path=str(dedupe_report_path),
        run_metadata_path=str(run_metadata_path),
    )


def rebuild_command(
    input_path: Path,
    data_dir: Path = Path("data"),
    limit: int = 20,
    summarizer_name: str = "placeholder",
    ollama_model: str = "gemma4:latest",
    ollama_url: str = "http://127.0.0.1:11434",
    script_style: str = "standard",
    topic_path: Path | None = None,
    editorial_skill_path: Path | None = None,
    editorial_model: str = "gemma4:latest",
    editorial_url: str = "http://127.0.0.1:11434",
) -> PipelineResult:
    run_at = datetime.now(timezone.utc)
    items = load_raw_items(input_path)
    topic_profile = _load_topic_profile(topic_path)
    editorial_skill = _load_editorial_skill(editorial_skill_path)
    editorial_reviewer = build_editorial_reviewer(
        editorial_skill,
        editorial_model,
        editorial_url,
        topic_profile,
    )
    dedupe_result, ranked, processed = _process_items(
        items,
        limit=limit,
        topic_profile=topic_profile,
        editorial_reviewer=editorial_reviewer,
    )
    ensure_data_dirs(data_dir)
    run_id = timestamp_slug(run_at)
    processed_path = save_processed_items(processed, data_dir, run_id=run_id, now=run_at)
    dedupe_report_path = save_dedupe_report(dedupe_result, data_dir, run_id, now=run_at)
    run_metadata_path = save_run_metadata(
        _run_metadata(
            collected=items,
            processed=processed,
            collection_failures=[],
            run_id=run_id,
            run_at=run_at,
            collect_limit=len(items),
            selection_limit=limit,
            topic_profile=topic_profile,
            editorial_skill=editorial_skill,
        ),
        data_dir,
        run_id,
        now=run_at,
    )
    summarizer = build_summarizer(summarizer_name, ollama_model, ollama_url, topic_profile)
    wiki_path, script_path = _write_pipeline_outputs(
        ranked,
        data_dir,
        run_id=run_id,
        run_at=run_at,
        summarizer=summarizer,
        script_style=script_style,
        topic_profile=topic_profile,
    )
    return PipelineResult(
        collected_count=len(items),
        deduped_count=len(dedupe_result.selected_items),
        selected_count=len(ranked),
        raw_path=str(input_path),
        wiki_path=str(wiki_path),
        script_path=str(script_path),
        processed_path=str(processed_path),
        dedupe_report_path=str(dedupe_report_path),
        run_metadata_path=str(run_metadata_path),
    )


def demo_command(
    data_dir: Path = Path("data"),
    limit: int = 20,
    topic_path: Path | None = None,
) -> PipelineResult:
    run_at = datetime.now(timezone.utc)
    topic_profile = _load_topic_profile(topic_path)
    ensure_data_dirs(data_dir)
    collected = DemoCollector("demo").collect(limit=limit)
    dedupe_result, ranked, processed = _process_items(
        collected,
        limit=limit,
        topic_profile=topic_profile,
    )
    run_id = timestamp_slug(run_at)
    raw_path = save_raw_items(collected, data_dir, now=run_at, run_id=run_id)
    processed_path = save_processed_items(processed, data_dir, run_id=run_id, now=run_at)
    dedupe_report_path = save_dedupe_report(dedupe_result, data_dir, run_id, now=run_at)
    run_metadata_path = save_run_metadata(
        _run_metadata(
            collected=collected,
            processed=processed,
            collection_failures=[],
            run_id=run_id,
            run_at=run_at,
            collect_limit=limit,
            selection_limit=limit,
            topic_profile=topic_profile,
        ),
        data_dir,
        run_id,
        now=run_at,
    )
    wiki_path, script_path = _write_pipeline_outputs(
        ranked,
        data_dir,
        run_id=run_id,
        run_at=run_at,
        topic_profile=topic_profile,
    )
    return PipelineResult(
        collected_count=len(collected),
        deduped_count=len(dedupe_result.selected_items),
        selected_count=len(ranked),
        raw_path=str(raw_path),
        wiki_path=str(wiki_path),
        script_path=str(script_path),
        processed_path=str(processed_path),
        dedupe_report_path=str(dedupe_report_path),
        run_metadata_path=str(run_metadata_path),
    )


def _write_pipeline_outputs(
    items: list[NewsItem],
    data_dir: Path,
    run_id: str,
    run_at: datetime,
    summarizer: Summarizer | None = None,
    script_style: str = "standard",
    topic_profile: TopicProfile | None = None,
) -> tuple[Path, Path]:
    wiki_paths = write_wiki_notes(
        items,
        data_dir / "wiki",
        now=run_at,
        summarizer=summarizer,
        clean_day=True,
        run_id=run_id,
        topic_profile=topic_profile,
    )
    notes = [load_wiki_notes(path)[0] for path in wiki_paths]
    script_path = write_script(
        notes,
        data_dir / "scripts" / f"{date_slug(run_at)}-{run_id}-daily.md",
        style=script_style,
        topic_profile=topic_profile,
    )
    write_topic_pages(notes, data_dir / "wiki" / "topics")
    shutil.copyfile(script_path, data_dir / "scripts" / "daily.md")
    wiki_path = wiki_paths[0].parent if wiki_paths else data_dir / "wiki"
    return wiki_path, script_path


def _process_items(
    items: list[NewsItem],
    limit: int,
    ranker_config: RankerConfig | None = None,
    topic_profile: TopicProfile | None = None,
    editorial_reviewer: EditorialReviewer | None = None,
) -> tuple[DedupeResult, list[NewsItem], list[NewsItem]]:
    dedupe_result = dedupe_items_with_report(items)
    if editorial_reviewer is None:
        ranked = rank_items(
            dedupe_result.selected_items,
            limit=limit,
            config=ranker_config,
            topic_profile=topic_profile,
        )
        processed = _with_dedupe_notes(ranked, dedupe_result)
        return dedupe_result, processed, processed

    candidate_limit = max(limit * 3, limit)
    candidates = rank_items(
        dedupe_result.selected_items,
        limit=candidate_limit,
        config=ranker_config,
        topic_profile=topic_profile,
    )
    reviewed = _with_editorial_reviews(candidates, editorial_reviewer)
    eligible = _editorial_daily_candidates(reviewed)
    if not eligible:
        eligible = reviewed
    ranked = rank_items(
        eligible,
        limit=limit,
        config=ranker_config,
        topic_profile=topic_profile,
    )
    ranked = _with_dedupe_notes(ranked, dedupe_result)
    selected_ids = {item.id for item in ranked}
    processed = _with_dedupe_notes(
        _with_selection_metadata(reviewed, selected_ids),
        dedupe_result,
    )
    return dedupe_result, ranked, processed


def _looks_processed(items: list[NewsItem]) -> bool:
    return bool(items) and all("score_breakdown" in item.metadata for item in items)


def _with_dedupe_notes(items: list[NewsItem], result: DedupeResult) -> list[NewsItem]:
    groups_by_selected: dict[str, list[dict[str, object]]] = {}
    for group in result.duplicate_groups:
        groups_by_selected.setdefault(group.selected_id, []).append(group.to_dict())

    processed: list[NewsItem] = []
    for item in items:
        metadata = dict(item.metadata)
        groups = groups_by_selected.get(item.id, [])
        metadata["dedupe"] = {
            "duplicate_count": sum(len(group["duplicate_ids"]) for group in groups),
            "duplicate_groups": groups,
        }
        processed.append(replace(item, metadata=metadata))
    return processed


def _with_editorial_reviews(
    items: list[NewsItem],
    editorial_reviewer: EditorialReviewer,
) -> list[NewsItem]:
    reviewed: list[NewsItem] = []
    for item in items:
        review = editorial_reviewer(item)
        metadata = dict(item.metadata)
        metadata["editorial_review"] = review.to_dict()
        reviewed.append(replace(item, metadata=metadata))
    return reviewed


def _editorial_daily_candidates(items: list[NewsItem]) -> list[NewsItem]:
    candidates: list[NewsItem] = []
    for item in items:
        review = _editorial_review(item)
        if review.read_in_daily and not review.wiki_only:
            candidates.append(item)
    return candidates


def _with_selection_metadata(items: list[NewsItem], selected_ids: set[str]) -> list[NewsItem]:
    processed: list[NewsItem] = []
    for item in items:
        metadata = dict(item.metadata)
        metadata["selected_for_daily"] = item.id in selected_ids
        processed.append(replace(item, metadata=metadata))
    return processed


def _editorial_review(item: NewsItem) -> EditorialReview:
    review = item.metadata.get("editorial_review")
    if isinstance(review, dict):
        return EditorialReview.from_dict(review)
    return EditorialReview()


def build_collectors(
    sources: tuple[SourceConfig, ...], source_filter: tuple[str, ...] = ()
) -> list[BaseCollector]:
    enabled_sources = [source for source in sources if source.enabled]
    if source_filter:
        requested = {value.strip().lower() for value in source_filter if value.strip()}
        enabled_sources = [
            source
            for source in enabled_sources
            if source.name.lower() in requested or source.type.lower() in requested
        ]
        if not enabled_sources:
            raise ValueError(f"No enabled sources matched: {', '.join(source_filter)}")

    if not enabled_sources:
        return [DemoCollector("demo")]

    collectors: list[BaseCollector] = []
    for source in enabled_sources:
        if source.type == "demo":
            collectors.append(DemoCollector(source.name))
        elif source.type == "rss":
            if not source.url:
                raise ValueError(f"RSS source {source.name} requires url")
            collectors.append(
                RssCollector(
                    source.name,
                    source.url,
                    timeout_seconds=_timeout_seconds(source),
                    rate_limit_seconds=_rate_limit_seconds(source),
                    retry_count=_retry_count(source),
                    retry_backoff_seconds=_retry_backoff_seconds(source),
                )
            )
        elif source.type == "arxiv":
            collectors.append(
                ArxivCollector(
                    source_name=source.name,
                    search_query=str(
                        source.params.get("search_query", "cat:cs.AI OR cat:cs.LG OR cat:cs.CL")
                    ),
                    max_results=int(source.params.get("max_results", 20)),
                    timeout_seconds=_timeout_seconds(source),
                    rate_limit_seconds=_rate_limit_seconds(source),
                    retry_count=_retry_count(source, default=1),
                    retry_backoff_seconds=_retry_backoff_seconds(source, default=2.0),
                )
            )
        elif source.type == "hackernews":
            collectors.append(
                HackerNewsCollector(
                    source_name=source.name,
                    query=str(source.params.get("query", "AI OR LLM OR OpenAI OR Anthropic")),
                    timeout_seconds=_timeout_seconds(source),
                    rate_limit_seconds=_rate_limit_seconds(source),
                )
            )
        else:
            raise ValueError(f"Unsupported source type: {source.type}")
    return collectors


def build_summarizer(
    name: str,
    ollama_model: str,
    ollama_url: str,
    topic_profile: TopicProfile | None = None,
):
    if name == "placeholder":
        return None
    if name == "ollama":
        print(f"Using local Ollama summarizer: {ollama_model} at {ollama_url}")
        return OllamaSummarizer(
            model=ollama_model,
            base_url=ollama_url,
            topic_profile=topic_profile,
        )
    raise ValueError(f"Unsupported summarizer: {name}")


def build_editorial_reviewer(
    skill: EditorialSkill | None,
    editorial_model: str,
    editorial_url: str,
    topic_profile: TopicProfile | None = None,
) -> EditorialReviewer | None:
    if skill is None:
        return None
    print(f"Using local Ollama editorial reviewer: {editorial_model} at {editorial_url}")
    return OllamaEditorialReviewer(
        skill=skill,
        model=editorial_model,
        base_url=editorial_url,
        topic_profile=topic_profile,
    )


def collect_all(collectors: list[BaseCollector], limit: int) -> list[NewsItem]:
    items, _ = collect_all_with_report(collectors, limit)
    return items


def collect_all_with_report(
    collectors: list[BaseCollector], limit: int
) -> tuple[list[NewsItem], list[dict[str, str]]]:
    items: list[NewsItem] = []
    failures: list[dict[str, str]] = []
    for collector in collectors:
        if collector.rate_limit_seconds:
            time.sleep(collector.rate_limit_seconds)
        try:
            items.extend(collector.collect(limit=limit))
        except CollectionError as exc:
            failures.append(
                {
                    "source": collector.source_name,
                    "error_type": "CollectionError",
                    "message": str(exc),
                }
            )
            print(f"warning: {collector.source_name}: {exc}; continuing with other sources")
        except Exception as exc:  # noqa: BLE001
            failures.append(
                {
                    "source": collector.source_name,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )
            print(
                f"warning: {collector.source_name}: unexpected collector failure: {exc}; "
                "continuing with other sources"
            )
    return items, failures


def _run_metadata(
    collected: list[NewsItem],
    processed: list[NewsItem],
    collection_failures: list[dict[str, str]],
    run_id: str,
    run_at: datetime | None = None,
    collect_limit: int | None = None,
    selection_limit: int | None = None,
    topic_profile: TopicProfile | None = None,
    editorial_skill: EditorialSkill | None = None,
) -> dict[str, object]:
    profile = topic_profile or TopicProfile()
    return {
        "run_id": run_id,
        "run_at": run_at.astimezone(timezone.utc).isoformat() if run_at else "",
        "topic_profile": profile.name,
        "editorial_skill": editorial_skill.name if editorial_skill else None,
        "collect_limit": collect_limit,
        "selection_limit": selection_limit,
        "collection_failures": collection_failures,
        "source_coverage": {
            "collected": _source_coverage(collected),
            "selected": _source_coverage(processed),
        },
    }


def _source_coverage(items: list[NewsItem]) -> dict[str, object]:
    by_source: dict[str, int] = {}
    by_source_type: dict[str, int] = {}
    for item in items:
        by_source[item.source] = by_source.get(item.source, 0) + 1
        by_source_type[item.source_type] = by_source_type.get(item.source_type, 0) + 1
    return {
        "total": len(items),
        "by_source": dict(sorted(by_source.items())),
        "by_source_type": dict(sorted(by_source_type.items())),
    }


def _timeout_seconds(source: SourceConfig) -> int:
    return int(source.params.get("timeout_seconds", 15))


def _rate_limit_seconds(source: SourceConfig) -> float:
    return float(source.params.get("rate_limit_seconds", 0.0))


def _retry_count(source: SourceConfig, default: int = 0) -> int:
    return int(source.params.get("retry_count", default))


def _retry_backoff_seconds(source: SourceConfig, default: float = 1.0) -> float:
    return float(source.params.get("retry_backoff_seconds", default))


def _print_preview(collected: list[NewsItem], ranked: list[NewsItem]) -> None:
    print("AI Signal dry run")
    print(f"Collected: {len(collected)}")
    print(f"Selected: {len(ranked)}")
    if not ranked:
        print("No items selected.")
        return
    print("Selected titles:")
    for index, item in enumerate(ranked, start=1):
        print(f"{index}. [{item.source}] {item.title}")


def _print_result(result: PipelineResult) -> None:
    print("AI Signal pipeline complete")
    print(f"Collected: {result.collected_count}")
    print(f"Deduped: {result.deduped_count}")
    print(f"Selected: {result.selected_count}")
    print(f"Raw JSON: {result.raw_path}")
    if result.processed_path:
        print(f"Processed JSON: {result.processed_path}")
    if result.dedupe_report_path:
        print(f"Dedupe report: {result.dedupe_report_path}")
    if result.run_metadata_path:
        print(f"Run metadata: {result.run_metadata_path}")
    print(f"Wiki notes: {result.wiki_path}")
    print(f"Radio script: {result.script_path}")
