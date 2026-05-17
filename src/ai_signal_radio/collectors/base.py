"""Collector interfaces and local demo data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta

from ai_signal_radio.models import NewsItem, utc_now


class CollectionError(RuntimeError):
    """Raised when a collector cannot fetch or parse its source."""


class BaseCollector(ABC):
    def __init__(self, source_name: str) -> None:
        self.source_name = source_name

    @abstractmethod
    def collect(self, limit: int = 20) -> list[NewsItem]:
        """Return normalized news items."""


class DemoCollector(BaseCollector):
    """A no-network collector for smoke tests and first-run demos."""

    def collect(self, limit: int = 20) -> list[NewsItem]:
        now = utc_now()
        items = [
            NewsItem(
                source=self.source_name,
                title="Open model evaluation harness adds multimodal benchmark support",
                url="https://example.local/open-model-eval-multimodal",
                summary=(
                    "A model evaluation project added image-and-text benchmark support, "
                    "making it easier to compare local and hosted AI systems."
                ),
                published_at=now - timedelta(hours=2),
                tags=("evaluation", "multimodal"),
            ),
            NewsItem(
                source=self.source_name,
                title="Researchers publish compact agent memory design for long tasks",
                url="https://example.local/agent-memory-design",
                summary=(
                    "The paper proposes a small persistent memory layer for agents that need "
                    "to maintain context across multi-step workflows."
                ),
                published_at=now - timedelta(hours=4),
                tags=("agents", "research"),
            ),
            NewsItem(
                source=self.source_name,
                title="VOICEVOX local narration workflow gains batch scripting example",
                url="https://example.local/voicevox-batch-scripting",
                summary=(
                    "A community recipe shows how to turn generated scripts into local audio "
                    "without sending text to a cloud API."
                ),
                published_at=now - timedelta(hours=6),
                tags=("tts", "local-first"),
            ),
        ]
        return items[:limit]
