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
    ) -> None:
        query = urlencode(
            {
                "search_query": search_query,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "max_results": str(max_results),
            }
        )
        super().__init__(source_name=source_name, url=f"https://export.arxiv.org/api/query?{query}")
