"""arXiv collector backed by the public Atom API."""

from __future__ import annotations

from urllib.parse import urlencode

from ai_signal_radio.collectors.rss import RssCollector


class ArxivCollector(RssCollector):
    def __init__(
        self,
        source_name: str,
        search_query: str = "cat:cs.AI OR cat:cs.CL OR cat:cs.LG",
        max_results: int = 20,
        timeout_seconds: int = 15,
        rate_limit_seconds: float = 0.0,
        retry_count: int = 1,
        retry_backoff_seconds: float = 2.0,
    ) -> None:
        query = urlencode(
            {
                "search_query": search_query,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "max_results": str(max_results),
            }
        )
        super().__init__(
            source_name=source_name,
            url=f"https://export.arxiv.org/api/query?{query}",
            timeout_seconds=timeout_seconds,
            rate_limit_seconds=rate_limit_seconds,
            source_type="arxiv",
            retry_count=retry_count,
            retry_backoff_seconds=retry_backoff_seconds,
        )
