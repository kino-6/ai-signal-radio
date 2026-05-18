"""Shared canonicalization helpers for news identity and dedupe."""

from __future__ import annotations

from hashlib import sha256
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PREFIXES = ("utm_",)
TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref"}


def canonical_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    query = sorted(
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
        and not key.lower().startswith(TRACKING_PREFIXES)
    )
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            urlencode(query, doseq=True),
            "",
        )
    )


def normalize_title(title: str) -> str:
    normalized = re.sub(r"\W+", " ", title.lower())
    return " ".join(normalized.split())


def canonical_key(url: str, title: str) -> str:
    payload = f"{canonical_url(url)}\0{normalize_title(title)}".encode("utf-8")
    return sha256(payload).hexdigest()[:16]


def content_hash(title: str, summary: str, content: str) -> str:
    payload = f"{title}\0{summary}\0{content}".encode("utf-8")
    return sha256(payload).hexdigest()[:16]
