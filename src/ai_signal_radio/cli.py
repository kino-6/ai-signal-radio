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
from ai_signal_radio.processors.wiki_writer import write_wiki
from ai_signal_radio.storage import date_slug, ensure_data_dirs, save_raw_items
from ai_signal_radio.tts.voicevox import VoicevoxClient


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        result = run_pipeline(
            config_path=args.config,
            data_dir=args.data_dir,
            limit=args.limit,
            skip_tts=args.skip_tts,
        )
        _print_result(result)
        return 0
    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-signal-radio",
        description="Collect AI news and generate local-first wiki notes and radio scripts.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run = subparsers.add_parser("run", help="Run the end-to-end MVP pipeline.")
    run.add_argument(
        "--config",
        type=Path,
        default=Path("config/sources.example.yml"),
        help="Path to source configuration YAML.",
    )
    run.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory for raw, wiki, script, and audio outputs.",
    )
    run.add_argument("--limit", type=int, default=10, help="Maximum items to keep after ranking.")
    run.add_argument("--skip-tts", action="store_true", help="Do not synthesize audio.")
    return parser


def run_pipeline(
    config_path: Path,
    data_dir: Path,
    limit: int = 10,
    skip_tts: bool = False,
) -> PipelineResult:
    config = load_config(config_path) if config_path.exists() else AppConfig()
    ensure_data_dirs(data_dir)

    collectors = build_collectors(config.sources)
    collected = collect_all(collectors, limit=max(limit * 2, limit))
    raw_path = save_raw_items(collected, data_dir)

    deduped = dedupe_items(collected)
    ranked = rank_items(deduped, limit=limit)

    wiki_path = write_wiki(ranked, data_dir / "wiki")
    script_path = write_script(ranked, data_dir / "scripts")

    audio_path: Path | None = None
    if config.tts.enabled and not skip_tts:
        client = VoicevoxClient(endpoint=config.tts.endpoint, speaker=config.tts.speaker)
        audio_path = client.synthesize_to_file(
            script_path.read_text(encoding="utf-8"),
            data_dir / "audio" / f"{date_slug()}-radio.wav",
        )

    return PipelineResult(
        collected_count=len(collected),
        deduped_count=len(deduped),
        selected_count=len(ranked),
        raw_path=str(raw_path),
        wiki_path=str(wiki_path),
        script_path=str(script_path),
        audio_path=str(audio_path) if audio_path else None,
    )


def build_collectors(sources: tuple[SourceConfig, ...]) -> list[BaseCollector]:
    enabled_sources = [source for source in sources if source.enabled]
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
                    search_query=str(source.params.get("search_query", "cat:cs.AI")),
                    max_results=int(source.params.get("max_results", 20)),
                )
            )
        elif source.type == "hackernews":
            collectors.append(
                HackerNewsCollector(
                    source_name=source.name,
                    query=str(source.params.get("query", "AI")),
                )
            )
        else:
            raise ValueError(f"Unsupported source type: {source.type}")
    return collectors


def collect_all(collectors: list[BaseCollector], limit: int) -> list[NewsItem]:
    items: list[NewsItem] = []
    for collector in collectors:
        try:
            items.extend(collector.collect(limit=limit))
        except CollectionError as exc:
            print(f"warning: {exc}")
    return items


def _print_result(result: PipelineResult) -> None:
    print("AI Signal Radio pipeline complete")
    print(f"Collected: {result.collected_count}")
    print(f"Deduped: {result.deduped_count}")
    print(f"Selected: {result.selected_count}")
    print(f"Raw JSON: {result.raw_path}")
    print(f"Wiki note: {result.wiki_path}")
    print(f"Radio script: {result.script_path}")
    if result.audio_path:
        print(f"Audio: {result.audio_path}")
