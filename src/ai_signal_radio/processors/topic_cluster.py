"""Lightweight topic clustering for near-duplicate news items."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import html
import re
from dataclasses import replace

from ai_signal_radio.config import TopicProfile
from ai_signal_radio.models import NewsItem

COMMON_WORDS = {
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
}

PRODUCT_STOPWORDS = {
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
}


@dataclass(frozen=True)
class TopicCluster:
    cluster_id: str
    label: str
    items: tuple[NewsItem, ...]
    reason: str
    keywords: tuple[str, ...]


def cluster_items(
    items: list[NewsItem],
    topic_profile: TopicProfile | None = None,
) -> list[NewsItem]:
    """Annotate items with simple deterministic topic cluster metadata.

    This is intentionally conservative. It should catch obvious same-topic
    follow-ups without requiring embeddings or hidden LLM calls.
    """

    profile = topic_profile or TopicProfile()
    clusters: list[TopicCluster] = []
    for item in items:
        match_index, reason, keywords = _find_cluster(clusters, item, profile)
        if match_index is None:
            clusters.append(
                TopicCluster(
                    cluster_id=_cluster_id(item, profile),
                    label=_cluster_label(item, profile),
                    items=(item,),
                    reason="single_item",
                    keywords=tuple(sorted(_keywords(item, profile))[:8]),
                )
            )
            continue

        cluster = clusters[match_index]
        clusters[match_index] = TopicCluster(
            cluster_id=cluster.cluster_id,
            label=cluster.label,
            items=(*cluster.items, item),
            reason=reason,
            keywords=tuple(sorted(set(cluster.keywords).union(keywords)))[:8],
        )

    clustered: list[NewsItem] = []
    for cluster in clusters:
        representative = cluster.items[0]
        for item in cluster.items:
            metadata = dict(item.metadata)
            metadata["topic_cluster"] = {
                "id": cluster.cluster_id,
                "label": cluster.label,
                "size": len(cluster.items),
                "representative_id": representative.id,
                "is_representative": item.id == representative.id,
                "related_item_ids": [related.id for related in cluster.items if related.id != item.id],
                "related_titles": [related.title for related in cluster.items if related.id != item.id],
                "related_sources": sorted({related.source for related in cluster.items}),
                "reason": cluster.reason,
                "keywords": list(cluster.keywords),
            }
            clustered.append(replace(item, metadata=metadata))
    return clustered


def _find_cluster(
    clusters: list[TopicCluster],
    item: NewsItem,
    profile: TopicProfile,
) -> tuple[int | None, str, tuple[str, ...]]:
    for index, cluster in enumerate(clusters):
        reason, keywords = _relation_reason(cluster.items[0], item, profile)
        if reason:
            return index, reason, keywords
    return None, "", ()


def _relation_reason(
    left: NewsItem,
    right: NewsItem,
    profile: TopicProfile,
) -> tuple[str, tuple[str, ...]]:
    left_products = _product_terms(left, profile)
    right_products = _product_terms(right, profile)
    product_overlap = tuple(sorted(left_products.intersection(right_products)))
    if product_overlap:
        return f"shared_product_terms: {', '.join(product_overlap)}", product_overlap

    left_terms = _keywords(left, profile)
    right_terms = _keywords(right, profile)
    overlap = tuple(sorted(left_terms.intersection(right_terms)))
    union_size = len(left_terms.union(right_terms))
    similarity = len(overlap) / union_size if union_size else 0.0
    if len(overlap) >= 8 and similarity >= 0.25:
        return f"keyword_overlap: {', '.join(overlap[:6])}", overlap[:8]
    return "", ()


def _cluster_id(item: NewsItem, profile: TopicProfile) -> str:
    payload = f"{item.source}\0{_cluster_label(item, profile)}".encode("utf-8")
    return f"topic-{sha256(payload).hexdigest()[:12]}"


def _cluster_label(item: NewsItem, profile: TopicProfile) -> str:
    products = sorted(_product_terms(item, profile))
    if products:
        return products[0]
    title = re.sub(r"^(Show|Ask|Tell) HN:\s*", "", item.title, flags=re.IGNORECASE)
    return " ".join(title.split())[:80]


def _product_terms(item: NewsItem, profile: TopicProfile) -> set[str]:
    title = _plain_text(item.title)
    text = _plain_text(f"{item.title} {item.content}")
    candidates = set(re.findall(r"\b[A-Z][A-Za-z0-9]{2,}\b", title))
    candidates.update(re.findall(r"\b([A-Z][A-Za-z0-9]{2,})\s+AI\b", text))
    stopwords = set(PRODUCT_STOPWORDS).union(profile.cluster_product_stopwords)
    terms = {
        token
        for token in candidates
        if token not in stopwords and not token.isupper() and not token.endswith("APIs")
    }
    return terms


def _keywords(item: NewsItem, profile: TopicProfile) -> set[str]:
    text = _plain_text(f"{item.title} {item.summary} {item.content[:2000]}")
    common_words = set(COMMON_WORDS).union(profile.cluster_common_words)
    tokens = {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9-]{2,}", text.lower())
        if token not in common_words and not token.isdigit()
    }
    return tokens


def _plain_text(value: str) -> str:
    text = html.unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())
