"""RSS and Atom feed collector."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from ai_signal_radio.collectors.base import BaseCollector, CollectionError
from ai_signal_radio.models import NewsItem


class RssCollector(BaseCollector):
    def __init__(
        self,
        source_name: str,
        url: str,
        timeout_seconds: int = 15,
        rate_limit_seconds: float = 0.0,
        source_type: str = "rss",
    ) -> None:
        super().__init__(source_name, rate_limit_seconds=rate_limit_seconds)
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.source_type = source_type

    def collect(self, limit: int = 20) -> list[NewsItem]:
        try:
            request = Request(self.url, headers={"User-Agent": "ai-signal/0.1"})
            with urlopen(request, timeout=self.timeout_seconds) as response:
                content = response.read()
            root = ElementTree.fromstring(content)
        except Exception as exc:  # noqa: BLE001
            raise CollectionError(f"failed to fetch or parse RSS/Atom feed: {exc}") from exc

        items = _parse_rss(root, self.source_name, self.source_type)
        if not items:
            items = _parse_atom(root, self.source_name, self.source_type)
        return items[:limit]


def _parse_rss(root: ElementTree.Element, source_name: str, source_type: str = "rss") -> list[NewsItem]:
    items: list[NewsItem] = []
    for element in root.findall(".//item"):
        title = _text(element, "title")
        link = _text(element, "link")
        summary = _text(element, "description")
        content = summary or _text(element, "content:encoded")
        published = _parse_date(_text(element, "pubDate"))
        if title and link:
            items.append(
                NewsItem(
                    source=source_name,
                    source_type=source_type,
                    title=title,
                    url=link,
                    summary=summary,
                    content=content,
                    published_at=published,
                    tags=(source_type,),
                )
            )
    return items


def _parse_atom(root: ElementTree.Element, source_name: str, source_type: str = "rss") -> list[NewsItem]:
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    items: list[NewsItem] = []
    entries = root.findall(".//atom:entry", namespace) or root.findall(".//entry")
    for entry in entries:
        title = _text(entry, "atom:title", namespace) or _text(entry, "title")
        summary = (
            _text(entry, "atom:summary", namespace)
            or _text(entry, "atom:content", namespace)
            or _text(entry, "summary")
        )
        link = _atom_link(entry, namespace)
        published = _parse_date(
            _text(entry, "atom:published", namespace)
            or _text(entry, "atom:updated", namespace)
            or _text(entry, "published")
        )
        if title and link:
            items.append(
                NewsItem(
                    source=source_name,
                    source_type=source_type,
                    title=title,
                    url=link,
                    summary=summary,
                    content=summary,
                    published_at=published,
                    tags=(source_type, "atom"),
                )
            )
    return items


def _text(
    element: ElementTree.Element, path: str, namespace: dict[str, str] | None = None
) -> str:
    try:
        child = element.find(path, namespace or {})
    except SyntaxError:
        return ""
    if child is None or child.text is None:
        return ""
    return " ".join(unescape(child.text).split())


def _atom_link(entry: ElementTree.Element, namespace: dict[str, str]) -> str:
    links = entry.findall("atom:link", namespace) or entry.findall("link")
    for link in links:
        href = link.attrib.get("href")
        if href and link.attrib.get("rel", "alternate") == "alternate":
            return href
    return links[0].attrib.get("href", "") if links else ""


def _parse_date(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
