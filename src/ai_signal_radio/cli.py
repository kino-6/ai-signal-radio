"""Command-line interface for ai-signal-radio."""

from __future__ import annotations

import argparse
from pathlib import Path

from ai_signal_radio.collectors.arxiv import ArxivCollector
from ai_signal_radio.collectors.base import BaseCollector, CollectionError, DemoCollector
from ai_signal_radio.collectors.hackernews import HackerNewsCollector
from ai_signal_radio.collectors.rss import RssCollector
from ai_signal_radio.config import AppConfig, SourceConfig, load_config
from ai_signal_radio.models import NewsItem, PipelineResult
from ai_signal_radio.processors.dedupe import dedupe_items
from ai_signal_radio.processors.ranker import rank_items
from ai_signal_radio.processors.script_writer import write_script
from ai_signal_radio.processors.wiki_writer import Summarizer, load_wiki_notes, write_wiki_notes
from ai_signal_radio.storage import ensure_data_dirs, load_raw_items, save_raw_items
from ai_signal_radio.summarizers.ollama import OllamaSummarizer
from ai_signal_radio.tts.voicevox import VoicevoxClient, markdown_to_speech_text


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

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
        )
        print(f"Wrote wiki notes: {len(paths)}")
        for path in paths:
            print(path)
        return 0
    if args.command == "script":
        path = script_command(input_path=args.input, output_path=args.output)
        print(f"Wrote script: {path}")
        return 0
    if args.command == "tts":
        path = tts_command(
            input_path=args.input,
            output_path=args.output,
            speaker=args.speaker,
            speed_scale=args.speed,
            pitch_scale=args.pitch,
            intonation_scale=args.intonation,
            voicevox_url=args.voicevox_url,
        )
        print(f"Wrote audio: {path}")
        return 0
    if args.command == "run":
        result = run_command(
            config_path=args.config,
            data_dir=args.data_dir,
            limit=args.limit,
            source_filter=tuple(args.source),
            dry_run=args.dry_run,
            summarizer_name=args.summarizer,
            ollama_model=args.ollama_model,
            ollama_url=args.ollama_url,
        )
        _print_result(result)
        return 0
    if args.command == "demo":
        result = demo_command(data_dir=args.data_dir, limit=args.limit)
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
    add_summarizer_args(wiki)

    script = subparsers.add_parser("script", help="Generate a radio-style Markdown script.")
    script.add_argument("--input", type=Path, required=True)
    script.add_argument("--output", type=Path, required=True)

    tts = subparsers.add_parser("tts", help="Synthesize a Markdown script with local VOICEVOX.")
    tts.add_argument("--input", type=Path, required=True)
    tts.add_argument("--output", type=Path, default=Path("data/audio/daily.wav"))
    tts.add_argument("--speaker", type=int, default=3, help="VOICEVOX speaker ID. 3 is Zundamon.")
    tts.add_argument("--speed", type=float, default=1.18, help="VOICEVOX speedScale.")
    tts.add_argument("--pitch", type=float, default=0.0, help="VOICEVOX pitchScale.")
    tts.add_argument("--intonation", type=float, default=1.0, help="VOICEVOX intonationScale.")
    tts.add_argument("--voicevox-url", default="http://127.0.0.1:50021")

    demo = subparsers.add_parser("demo", help="Run a fully local sample pipeline.")
    demo.add_argument("--data-dir", type=Path, default=Path("data"))
    demo.add_argument("--limit", type=int, default=20)

    run = subparsers.add_parser("run", help="Run collect, wiki, and script generation.")
    run.add_argument("--config", type=Path, default=Path("config/sources.example.yml"))
    run.add_argument("--data-dir", type=Path, default=Path("data"))
    run.add_argument("--limit", type=int, default=20)
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


def collect_command(
    config_path: Path,
    limit: int = 20,
    data_dir: Path = Path("data"),
    source_filter: tuple[str, ...] = (),
    dry_run: bool = False,
) -> Path | None:
    config = load_config(config_path) if config_path.exists() else AppConfig()
    items = collect_all(build_collectors(config.sources, source_filter=source_filter), limit=limit)
    ranked = rank_items(dedupe_items(items), limit=limit)
    if dry_run:
        _print_preview(items, ranked)
        return None
    ensure_data_dirs(data_dir)
    return save_raw_items(items, data_dir)


def wiki_command(
    input_path: Path,
    output_dir: Path,
    summarizer_name: str = "placeholder",
    ollama_model: str = "gemma4:latest",
    ollama_url: str = "http://127.0.0.1:11434",
) -> list[Path]:
    items = load_raw_items(input_path)
    ranked = rank_items(dedupe_items(items), limit=len(items) or 20)
    summarizer = build_summarizer(summarizer_name, ollama_model, ollama_url)
    return write_wiki_notes(ranked, output_dir, summarizer=summarizer, clean_day=True)


def script_command(input_path: Path, output_path: Path) -> Path:
    notes = load_wiki_notes(input_path)
    notes = sorted(notes, key=lambda note: note.score, reverse=True)
    return write_script(notes, output_path)


def tts_command(
    input_path: Path,
    output_path: Path,
    speaker: int = 3,
    speed_scale: float = 1.18,
    pitch_scale: float = 0.0,
    intonation_scale: float = 1.0,
    voicevox_url: str = "http://127.0.0.1:50021",
) -> Path:
    client = VoicevoxClient(base_url=voicevox_url)
    if not client.healthcheck():
        raise RuntimeError(f"VOICEVOX engine is not available at {voicevox_url}")
    markdown = input_path.read_text(encoding="utf-8")
    speech_text = markdown_to_speech_text(markdown)
    return client.synthesize_to_wav(
        speech_text,
        output_path,
        speaker=speaker,
        speed_scale=speed_scale,
        pitch_scale=pitch_scale,
        intonation_scale=intonation_scale,
    )


def run_command(
    config_path: Path,
    data_dir: Path = Path("data"),
    limit: int = 20,
    source_filter: tuple[str, ...] = (),
    dry_run: bool = False,
    summarizer_name: str = "placeholder",
    ollama_model: str = "gemma4:latest",
    ollama_url: str = "http://127.0.0.1:11434",
) -> PipelineResult:
    config = load_config(config_path) if config_path.exists() else AppConfig()
    collected = collect_all(build_collectors(config.sources, source_filter=source_filter), limit=limit)
    deduped = dedupe_items(collected)
    ranked = rank_items(deduped, limit=limit)

    if dry_run:
        _print_preview(collected, ranked)
        return PipelineResult(
            collected_count=len(collected),
            deduped_count=len(deduped),
            selected_count=len(ranked),
            raw_path="dry-run: not written",
            wiki_path="dry-run: not written",
            script_path="dry-run: not written",
        )

    ensure_data_dirs(data_dir)
    raw_path = save_raw_items(collected, data_dir)
    summarizer = build_summarizer(summarizer_name, ollama_model, ollama_url)
    wiki_path, script_path = _write_pipeline_outputs(ranked, data_dir, summarizer=summarizer)
    return PipelineResult(
        collected_count=len(collected),
        deduped_count=len(deduped),
        selected_count=len(ranked),
        raw_path=str(raw_path),
        wiki_path=str(wiki_path),
        script_path=str(script_path),
    )


def demo_command(data_dir: Path = Path("data"), limit: int = 20) -> PipelineResult:
    ensure_data_dirs(data_dir)
    collected = DemoCollector("demo").collect(limit=limit)
    deduped = dedupe_items(collected)
    ranked = rank_items(deduped, limit=limit)
    raw_path = save_raw_items(collected, data_dir)
    wiki_path, script_path = _write_pipeline_outputs(ranked, data_dir)
    return PipelineResult(
        collected_count=len(collected),
        deduped_count=len(deduped),
        selected_count=len(ranked),
        raw_path=str(raw_path),
        wiki_path=str(wiki_path),
        script_path=str(script_path),
    )


def _write_pipeline_outputs(
    items: list[NewsItem],
    data_dir: Path,
    summarizer: Summarizer | None = None,
) -> tuple[Path, Path]:
    wiki_paths = write_wiki_notes(
        items,
        data_dir / "wiki",
        summarizer=summarizer,
        clean_day=True,
    )
    notes = [load_wiki_notes(path)[0] for path in wiki_paths]
    script_path = write_script(notes, data_dir / "scripts" / "daily.md")
    wiki_path = wiki_paths[0].parent if wiki_paths else data_dir / "wiki"
    return wiki_path, script_path


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
            collectors.append(RssCollector(source.name, source.url))
        elif source.type == "arxiv":
            collectors.append(
                ArxivCollector(
                    source_name=source.name,
                    search_query=str(
                        source.params.get("search_query", "cat:cs.AI OR cat:cs.LG OR cat:cs.CL")
                    ),
                    max_results=int(source.params.get("max_results", 20)),
                )
            )
        elif source.type == "hackernews":
            collectors.append(
                HackerNewsCollector(
                    source_name=source.name,
                    query=str(source.params.get("query", "AI OR LLM OR OpenAI OR Anthropic")),
                )
            )
        else:
            raise ValueError(f"Unsupported source type: {source.type}")
    return collectors


def build_summarizer(name: str, ollama_model: str, ollama_url: str):
    if name == "placeholder":
        return None
    if name == "ollama":
        print(f"Using local Ollama summarizer: {ollama_model} at {ollama_url}")
        return OllamaSummarizer(model=ollama_model, base_url=ollama_url)
    raise ValueError(f"Unsupported summarizer: {name}")


def collect_all(collectors: list[BaseCollector], limit: int) -> list[NewsItem]:
    items: list[NewsItem] = []
    for collector in collectors:
        try:
            items.extend(collector.collect(limit=limit))
        except CollectionError as exc:
            print(f"warning: {collector.source_name}: {exc}; continuing with other sources")
        except Exception as exc:  # noqa: BLE001
            print(
                f"warning: {collector.source_name}: unexpected collector failure: {exc}; "
                "continuing with other sources"
            )
    return items


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
    print(f"Wiki notes: {result.wiki_path}")
    print(f"Radio script: {result.script_path}")
