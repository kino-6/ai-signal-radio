from xml.etree import ElementTree

from ai_signal_radio.collectors.arxiv import ArxivCollector
from ai_signal_radio.collectors.hackernews import parse_hackernews_payload
from ai_signal_radio.collectors.rss import _parse_atom, _parse_rss


def test_parse_rss_fixture_without_network() -> None:
    root = ElementTree.fromstring(
        """
        <rss><channel>
          <item>
            <title>AI model update</title>
            <link>https://example.com/ai-model-update</link>
            <description>Summary from feed.</description>
            <pubDate>Fri, 02 Jan 2026 03:04:00 GMT</pubDate>
          </item>
        </channel></rss>
        """
    )

    items = _parse_rss(root, "example-rss")

    assert len(items) == 1
    assert items[0].title == "AI model update"
    assert items[0].source_type == "rss"
    assert items[0].content == "Summary from feed."


def test_parse_atom_fixture_without_network() -> None:
    root = ElementTree.fromstring(
        """
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>LLM agent paper</title>
            <link href="https://example.com/llm-agent-paper" />
            <summary>Atom summary.</summary>
            <published>2026-01-02T03:04:00Z</published>
          </entry>
        </feed>
        """
    )

    items = _parse_atom(root, "example-atom")

    assert len(items) == 1
    assert items[0].url == "https://example.com/llm-agent-paper"
    assert items[0].source_type == "rss"
    assert "atom" in items[0].tags


def test_parse_hackernews_payload_without_network() -> None:
    payload = {
        "hits": [
            {
                "title": "OpenAI LLM tooling discussion",
                "url": "https://example.com/hn",
                "created_at": "2026-01-02T03:04:00Z",
                "points": 123,
                "objectID": "42",
            }
        ]
    }

    items = parse_hackernews_payload(payload, "hacker-news-ai")

    assert len(items) == 1
    assert items[0].metadata["points"] == 123
    assert items[0].source_type == "hackernews"


def test_arxiv_collector_builds_expected_query_url() -> None:
    collector = ArxivCollector("arxiv-ai", max_results=5, timeout_seconds=7, rate_limit_seconds=0.5)

    assert "cat%3Acs.AI" in collector.url
    assert "max_results=5" in collector.url
    assert collector.source_type == "arxiv"
    assert collector.timeout_seconds == 7
    assert collector.rate_limit_seconds == 0.5
