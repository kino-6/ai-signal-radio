"""Configuration loading for source and TTS settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_SCORE_KEYWORDS = (
    "model",
    "agent",
    "openai",
    "anthropic",
    "google",
    "hugging face",
    "ai",
    "llm",
)

DEFAULT_OFFICIAL_SOURCES = (
    "openai",
    "anthropic",
    "google",
    "hugging face",
    "microsoft",
    "meta",
)

DEFAULT_CLUSTER_COMMON_WORDS = (
    "about",
    "agent",
    "agents",
    "android",
    "anthropic",
    "app",
    "apps",
    "assistant",
    "built",
    "cloud",
    "code",
    "coding",
    "does",
    "doesn",
    "doing",
    "from",
    "gemini",
    "google",
    "hacker",
    "have",
    "hosted",
    "local",
    "model",
    "models",
    "news",
    "openai",
    "post",
    "show",
    "source",
    "that",
    "their",
    "this",
    "using",
    "with",
    "works",
    "would",
    "your",
)

DEFAULT_CLUSTER_PRODUCT_STOPWORDS = (
    "AI",
    "API",
    "APIs",
    "About",
    "Apen",
    "Amazon",
    "Ask",
    "AWS",
    "Azure",
    "Bedrock",
    "Claude",
    "Deepseek",
    "Gemini",
    "GitHub",
    "Google",
    "How",
    "HN",
    "LLM",
    "Mistral",
    "Ollama",
    "Open",
    "OpenAI",
    "Pricing",
    "Source",
    "Show",
    "Tell",
    "The",
    "Things",
    "This",
    "Website",
)


@dataclass(frozen=True)
class TopicProfile:
    name: str = "ai"
    program_title: str = "Daily AI Signal Radio"
    deep_dive_title: str = "AI Signal Radio Deep Dive"
    briefing_intro: str = "今日のAIニュースです。"
    deep_dive_intro: str = "AI Signal Radio の深掘りです。"
    audience: str = "AI開発者"
    interpretation_lens: str = "モデル、開発ツール、研究動向、ローカルAI運用"
    closing_line: str = "それでは、今日もよい開発を。"
    focus_action_line: str = (
        "今日の実装観点は、気になった話題を読むだけで終わらせず、"
        "小さく試せる形に分解することです。"
    )
    default_tags: tuple[str, ...] = ("ai",)
    action_items: tuple[str, ...] = (
        "元情報を読み、具体的に何が変わったか確認する。",
        "このプロジェクトの監視リストを更新する必要があるか判断する。",
    )
    score_keywords: tuple[str, ...] = DEFAULT_SCORE_KEYWORDS
    official_sources: tuple[str, ...] = DEFAULT_OFFICIAL_SOURCES
    cluster_common_words: tuple[str, ...] = DEFAULT_CLUSTER_COMMON_WORDS
    cluster_product_stopwords: tuple[str, ...] = DEFAULT_CLUSTER_PRODUCT_STOPWORDS


@dataclass(frozen=True)
class EditorialSkill:
    name: str = "default"
    audience: str = "AI開発者"
    purpose: str = "収集したニュースから、日次ラジオで読む価値がある項目を選ぶ"
    accept: tuple[str, ...] = field(default_factory=tuple)
    reject: tuple[str, ...] = field(default_factory=tuple)
    framing: str = "聞いたあとに確認する観点を短く示す"
    relevance_threshold: int = 3


@dataclass(frozen=True)
class SourceConfig:
    name: str
    type: str
    enabled: bool = True
    url: str | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TTSConfig:
    enabled: bool = False
    endpoint: str = "http://127.0.0.1:50021"
    speaker: int = 3
    speed_scale: float = 1.18
    pitch_scale: float = 0.0
    intonation_scale: float = 1.0
    pronunciation_profile: str | None = None


@dataclass(frozen=True)
class RankerConfig:
    keyword_bonus: float = 2.0
    official_source_bonus: float = 4.0
    research_bonus: float = 2.0
    hn_points_divisor: float = 100.0
    hn_points_cap: float = 3.0
    max_topic_cluster_items: int = 1
    min_source_types: dict[str, int] = field(default_factory=lambda: {"arxiv": 1})
    max_source_types: dict[str, int] = field(default_factory=lambda: {"hackernews": 3})


@dataclass(frozen=True)
class AppConfig:
    sources: tuple[SourceConfig, ...] = field(default_factory=tuple)
    tts: TTSConfig = field(default_factory=TTSConfig)
    ranker: RankerConfig = field(default_factory=RankerConfig)
    topic: TopicProfile = field(default_factory=TopicProfile)


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    sources = tuple(_load_source(item) for item in raw.get("sources", []))
    tts = _load_tts(raw.get("tts", {}))
    ranker = _load_ranker(raw.get("ranker", {}))
    topic = _load_topic_profile(raw.get("topic", {}))
    return AppConfig(sources=sources, tts=tts, ranker=ranker, topic=topic)


def load_topic_profile(path: Path) -> TopicProfile:
    if not path.exists():
        raise FileNotFoundError(f"Topic profile not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError("topic profile must be a mapping")
    return _load_topic_profile(raw)


def load_editorial_skill(path: Path) -> EditorialSkill:
    if not path.exists():
        raise FileNotFoundError(f"Editorial skill not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError("editorial skill must be a mapping")
    return _load_editorial_skill(raw)


def _load_source(raw: dict[str, Any]) -> SourceConfig:
    params = raw.get("params") or {}
    if not isinstance(params, dict):
        raise ValueError("source params must be a mapping")
    return SourceConfig(
        name=str(raw.get("name", "")).strip(),
        type=str(raw.get("type", "")).strip().lower(),
        enabled=bool(raw.get("enabled", True)),
        url=str(raw["url"]).strip() if raw.get("url") else None,
        params=params,
    )


def _load_tts(raw: dict[str, Any]) -> TTSConfig:
    return TTSConfig(
        enabled=bool(raw.get("enabled", False)),
        endpoint=str(raw.get("endpoint", "http://127.0.0.1:50021")).rstrip("/"),
        speaker=int(raw.get("speaker", 3)),
        speed_scale=float(raw.get("speed_scale", raw.get("speed", 1.18))),
        pitch_scale=float(raw.get("pitch_scale", raw.get("pitch", 0.0))),
        intonation_scale=float(raw.get("intonation_scale", raw.get("intonation", 1.0))),
        pronunciation_profile=(
            str(raw["pronunciation_profile"]) if raw.get("pronunciation_profile") else None
        ),
    )


def _load_ranker(raw: dict[str, Any]) -> RankerConfig:
    return RankerConfig(
        keyword_bonus=float(raw.get("keyword_bonus", 2.0)),
        official_source_bonus=float(raw.get("official_source_bonus", 4.0)),
        research_bonus=float(raw.get("research_bonus", 2.0)),
        hn_points_divisor=float(raw.get("hn_points_divisor", 100.0)),
        hn_points_cap=float(raw.get("hn_points_cap", 3.0)),
        max_topic_cluster_items=max(1, int(raw.get("max_topic_cluster_items", 1))),
        min_source_types=_int_mapping(raw.get("min_source_types"), {"arxiv": 1}),
        max_source_types=_int_mapping(raw.get("max_source_types"), {"hackernews": 3}),
    )


def _load_topic_profile(raw: Any) -> TopicProfile:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("topic profile config must be a mapping")
    default = TopicProfile()
    return TopicProfile(
        name=str(raw.get("name", default.name)).strip() or default.name,
        program_title=str(raw.get("program_title", default.program_title)).strip()
        or default.program_title,
        deep_dive_title=str(raw.get("deep_dive_title", default.deep_dive_title)).strip()
        or default.deep_dive_title,
        briefing_intro=str(raw.get("briefing_intro", default.briefing_intro)).strip()
        or default.briefing_intro,
        deep_dive_intro=str(raw.get("deep_dive_intro", default.deep_dive_intro)).strip()
        or default.deep_dive_intro,
        audience=str(raw.get("audience", default.audience)).strip() or default.audience,
        interpretation_lens=str(
            raw.get("interpretation_lens", default.interpretation_lens)
        ).strip()
        or default.interpretation_lens,
        closing_line=str(raw.get("closing_line", default.closing_line)).strip()
        or default.closing_line,
        focus_action_line=str(raw.get("focus_action_line", default.focus_action_line)).strip()
        or default.focus_action_line,
        default_tags=_str_tuple(raw.get("default_tags"), default.default_tags),
        action_items=_str_tuple(raw.get("action_items"), default.action_items),
        score_keywords=_str_tuple(raw.get("score_keywords"), default.score_keywords),
        official_sources=_str_tuple(raw.get("official_sources"), default.official_sources),
        cluster_common_words=_str_tuple(
            raw.get("cluster_common_words"), default.cluster_common_words
        ),
        cluster_product_stopwords=_str_tuple(
            raw.get("cluster_product_stopwords"), default.cluster_product_stopwords
        ),
    )


def _load_editorial_skill(raw: Any) -> EditorialSkill:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("editorial skill config must be a mapping")
    default = EditorialSkill()
    radio_style = raw.get("radio_style") or {}
    if radio_style is None:
        radio_style = {}
    if not isinstance(radio_style, dict):
        raise ValueError("editorial radio_style must be a mapping")
    threshold = int(raw.get("relevance_threshold", default.relevance_threshold))
    return EditorialSkill(
        name=str(raw.get("name", default.name)).strip() or default.name,
        audience=str(raw.get("audience", default.audience)).strip() or default.audience,
        purpose=str(raw.get("purpose", default.purpose)).strip() or default.purpose,
        accept=_str_tuple(raw.get("accept"), default.accept),
        reject=_str_tuple(raw.get("reject"), default.reject),
        framing=str(radio_style.get("framing", raw.get("framing", default.framing))).strip()
        or default.framing,
        relevance_threshold=max(1, min(5, threshold)),
    )


def _str_tuple(value: Any, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return default
    if isinstance(value, str):
        items = (value,)
    elif isinstance(value, list | tuple):
        items = tuple(str(item).strip() for item in value)
    else:
        raise ValueError("topic profile list fields must be strings or lists")
    cleaned = tuple(item for item in items if item)
    return cleaned or default


def _int_mapping(value: Any, default: dict[str, int]) -> dict[str, int]:
    if value is None:
        return dict(default)
    if not isinstance(value, dict):
        raise ValueError("source type diversity config must be a mapping")
    return {
        str(key).strip().lower(): max(0, int(count))
        for key, count in value.items()
        if str(key).strip()
    }
