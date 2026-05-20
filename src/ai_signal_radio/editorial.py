"""Optional local editorial review pass for topic-specific radio selection."""

from __future__ import annotations

import json
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from ai_signal_radio.config import EditorialSkill, TopicProfile
from ai_signal_radio.models import EditorialReview, NewsItem
from ai_signal_radio.processors.wiki_note_builder import spoken_title_from_item

Transport = Callable[[Request, int], bytes]
EditorialReviewer = Callable[[NewsItem], EditorialReview]


class OllamaEditorialReviewer:
    """Ask a local Ollama model whether an item belongs in the daily briefing."""

    def __init__(
        self,
        skill: EditorialSkill,
        model: str = "gemma4:latest",
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: int = 120,
        transport: Transport | None = None,
        topic_profile: TopicProfile | None = None,
    ) -> None:
        self.skill = skill
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport or _default_transport
        self.topic_profile = topic_profile or TopicProfile()

    def __call__(self, item: NewsItem) -> EditorialReview:
        fallback = fallback_editorial_review(item, self.skill)
        payload = {
            "model": self.model,
            "prompt": build_editorial_prompt(item, self.skill, self.topic_profile),
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        }
        request = Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            raw = self.transport(request, self.timeout_seconds)
            response = json.loads(raw.decode("utf-8"))
            generated = json.loads(response.get("response", "{}"))
            return review_from_generated(generated, fallback, self.skill)
        except (json.JSONDecodeError, KeyError, TypeError, URLError, TimeoutError, OSError) as exc:
            print(
                f"warning: Ollama editorial reviewer failed for {item.title}: {exc}; "
                "using fallback"
            )
            return fallback


def fallback_editorial_review(
    item: NewsItem,
    skill: EditorialSkill | None = None,
) -> EditorialReview:
    skill = skill or EditorialSkill()
    score = 3
    if item.score >= 8:
        score = 4
    if item.score >= 12:
        score = 5
    return EditorialReview(
        relevance_score=score,
        read_in_daily=score >= skill.relevance_threshold,
        wiki_only=score < skill.relevance_threshold,
        why_relevant=f"{item.source_type} 系の情報として、{skill.audience}が確認する価値があります。",
        topic_angle=skill.framing,
        spoken_title=spoken_title_from_item(item),
        one_line_takeaway=item.summary or f"{item.source} が「{spoken_title_from_item(item)}」について報じています。",
        listen_action="自分の業務や開発プロセスに当てはめて、試せる箇所を1つ確認します。",
        reject_reason="",
    )


def build_editorial_prompt(
    item: NewsItem,
    skill: EditorialSkill,
    topic_profile: TopicProfile | None = None,
) -> str:
    profile = topic_profile or TopicProfile()
    score_breakdown = item.metadata.get("score_breakdown", {})
    topic_cluster = item.metadata.get("topic_cluster", {})
    return f"""あなたはローカル日次ニュース番組の編集者です。
入力された情報だけを根拠に、topic sample として日次ラジオで読むべきか判定してください。
事実を追加で捏造しないでください。判断に迷う場合は wiki_only にしてください。

Return only JSON with these keys:
- relevance_score: 1から5の整数。{skill.audience}にどれだけ関係するか。
- read_in_daily: 日次ラジオで読むなら true。
- wiki_only: wiki に残すだけなら true。
- why_relevant: 関係がある、または薄い理由を短い日本語で説明。
- topic_angle: この topic で見るなら何の論点か。
- spoken_title: 耳で聞きやすい短い日本語見出し。
- one_line_takeaway: ラジオ本文で使える1文の要点。
- listen_action: 聞いたあとに確認する観点を1文で説明。
- reject_reason: 読まない場合の理由。読む場合は空文字。

Editorial skill: {skill.name}
Audience: {skill.audience}
Purpose: {skill.purpose}
Accept:
{_bullet_lines(skill.accept)}
Reject:
{_bullet_lines(skill.reject)}
Radio framing: {skill.framing}

Topic profile: {profile.name}
Topic audience: {profile.audience}
Topic lens: {profile.interpretation_lens}

Title: {item.title}
Source: {item.source}
Source type: {item.source_type}
URL: {item.url}
Published at: {item.published_at.isoformat()}
Summary: {item.summary}
Content: {item.content}
Tags: {", ".join(item.tags)}
Score: {item.score}
Score breakdown: {json.dumps(score_breakdown, ensure_ascii=False)}
Topic cluster: {json.dumps(topic_cluster, ensure_ascii=False)}
"""


def review_from_generated(
    generated: object,
    fallback: EditorialReview,
    skill: EditorialSkill,
) -> EditorialReview:
    if not isinstance(generated, dict):
        return fallback
    relevance_score = _int_field(generated.get("relevance_score"), fallback.relevance_score)
    read_in_daily = _bool_field(generated.get("read_in_daily"), relevance_score >= skill.relevance_threshold)
    wiki_only = _bool_field(generated.get("wiki_only"), not read_in_daily)
    if wiki_only:
        read_in_daily = False
    return EditorialReview(
        relevance_score=relevance_score,
        read_in_daily=read_in_daily,
        wiki_only=wiki_only,
        why_relevant=_text_field(generated.get("why_relevant"), fallback.why_relevant),
        topic_angle=_text_field(
            generated.get("topic_angle", generated.get("process_improvement_angle")),
            fallback.topic_angle,
        ),
        spoken_title=_text_field(generated.get("spoken_title"), fallback.spoken_title, max_chars=80),
        one_line_takeaway=_text_field(
            generated.get("one_line_takeaway"),
            fallback.one_line_takeaway,
            max_chars=140,
        ),
        listen_action=_text_field(
            generated.get("listen_action"),
            fallback.listen_action,
            max_chars=140,
        ),
        reject_reason=_text_field(generated.get("reject_reason"), "", max_chars=160),
    )


def _default_transport(request: Request, timeout_seconds: int) -> bytes:
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def _bullet_lines(items: tuple[str, ...]) -> str:
    if not items:
        return "- 指定なし"
    return "\n".join(f"- {item}" for item in items)


def _text_field(value: object, fallback: str, max_chars: int = 320) -> str:
    text = str(value).strip() if isinstance(value, str) else ""
    if not text:
        text = fallback
    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "…"
    return text


def _int_field(value: object, fallback: int) -> int:
    try:
        return max(1, min(5, int(value)))
    except (TypeError, ValueError):
        return fallback


def _bool_field(value: object, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    return fallback
