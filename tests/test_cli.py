from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from searchstack.adapters.fetch import HTMLContentExtractor
from searchstack.adapters.wikipedia import WikipediaSearchAdapter
from searchstack.cli import main
from searchstack.models import FetchedDocument, SearchResult
from searchstack.services import run_search


class _StubSearchAdapter:
    source_name = "stub"

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        assert query == "openclaw"
        return [
            SearchResult(
                title="OpenClaw",
                url="https://example.com/openclaw",
                snippet="Local-first search stack",
                source="stub",
                rank=1,
            )
        ][:limit]


class _NamedSearchAdapter:
    def __init__(self, source_name: str, results: list[SearchResult]) -> None:
        self.source_name = source_name
        self._results = results

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        assert query == "openclaw"
        return self._results[:limit]


class _StubFetchAdapter:
    def fetch(self, url: str) -> FetchedDocument:
        assert url == "https://example.com/openclaw"
        return FetchedDocument(
            url=url,
            final_url=url,
            title="OpenClaw",
            excerpt="Local-first search stack",
            content="OpenClaw builds a local-first search stack.",
            status_code=200,
            content_type="text/html",
        )


class _FailingFetchAdapter:
    def fetch(self, url: str) -> FetchedDocument:
        raise TimeoutError(f"timed out fetching {url}")


class SearchStackCLITest(unittest.TestCase):
    def test_search_command_prints_json_envelope(self) -> None:
        stdout = io.StringIO()
        with patch(
            "searchstack.cli.create_search_adapters",
            return_value=[_StubSearchAdapter()],
        ):
            with redirect_stdout(stdout):
                exit_code = main(["search", "openclaw"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["query"], "openclaw")
        self.assertEqual(payload["sources"], ["duckduckgo"])
        self.assertEqual(payload["result_count"], 1)
        self.assertEqual(payload["results"][0]["title"], "OpenClaw")
        self.assertEqual(payload["results"][0]["normalized_url"], "https://example.com/openclaw")
        self.assertEqual(payload["results"][0]["source_ranks"], {"stub": 1})

    def test_fetch_command_prints_document_envelope(self) -> None:
        stdout = io.StringIO()
        with patch(
            "searchstack.cli.create_fetch_adapter",
            return_value=_StubFetchAdapter(),
        ):
            with redirect_stdout(stdout):
                exit_code = main(["fetch", "https://example.com/openclaw"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["url"], "https://example.com/openclaw")
        self.assertEqual(payload["document"]["title"], "OpenClaw")
        self.assertEqual(payload["document"]["status_code"], 200)
        self.assertEqual(payload["document"]["final_url"], "https://example.com/openclaw")
        self.assertEqual(payload["document"]["content_type"], "text/html")
        self.assertIn("local-first search stack", payload["document"]["content"].lower())

    def test_query_command_searches_then_fetches(self) -> None:
        stdout = io.StringIO()
        with patch(
            "searchstack.cli.create_search_adapters",
            return_value=[_StubSearchAdapter()],
        ), patch(
            "searchstack.cli.create_fetch_adapter",
            return_value=_StubFetchAdapter(),
        ):
            with redirect_stdout(stdout):
                exit_code = main(["query", "openclaw", "--limit", "1"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["result_count"], 1)
        self.assertEqual(payload["results"][0]["search"]["url"], "https://example.com/openclaw")
        self.assertEqual(payload["results"][0]["document"]["status_code"], 200)
        self.assertEqual(payload["results"][0]["document"]["content_type"], "text/html")
        self.assertEqual(payload["results"][0]["rank"], 1)
        self.assertEqual(payload["results"][0]["sources"], ["stub"])

    def test_query_command_keeps_results_when_fetch_fails(self) -> None:
        stdout = io.StringIO()
        with patch(
            "searchstack.cli.create_search_adapters",
            return_value=[_StubSearchAdapter()],
        ), patch(
            "searchstack.cli.create_fetch_adapter",
            return_value=_FailingFetchAdapter(),
        ):
            with redirect_stdout(stdout):
                exit_code = main(["query", "openclaw", "--limit", "1"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["results"][0]["search"]["url"], "https://example.com/openclaw")
        self.assertIsNone(payload["results"][0]["document"]["status_code"])
        self.assertEqual(payload["results"][0]["document"]["final_url"], "https://example.com/openclaw")
        self.assertIn("TimeoutError", payload["results"][0]["document"]["error"])

    def test_search_command_passes_all_sources_to_factory(self) -> None:
        stdout = io.StringIO()

        def _factory(sources: tuple[str, ...]) -> list[_StubSearchAdapter]:
            self.assertEqual(sources, ("duckduckgo", "wikipedia"))
            return [_StubSearchAdapter()]

        with patch("searchstack.cli.create_search_adapters", side_effect=_factory):
            with redirect_stdout(stdout):
                exit_code = main(["search", "openclaw", "--source", "all"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["results"][0]["source"], "stub")

    def test_query_command_passes_multiple_sources_to_factory(self) -> None:
        stdout = io.StringIO()

        def _factory(sources: tuple[str, ...]) -> list[_StubSearchAdapter]:
            self.assertEqual(sources, ("wikipedia", "duckduckgo"))
            return [_StubSearchAdapter()]

        with patch("searchstack.cli.create_search_adapters", side_effect=_factory), patch(
            "searchstack.cli.create_fetch_adapter",
            return_value=_StubFetchAdapter(),
        ):
            with redirect_stdout(stdout):
                exit_code = main(["query", "openclaw", "--source", "wikipedia,duckduckgo", "--limit", "1"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["results"][0]["source"], "stub")

    def test_limit_must_be_positive(self) -> None:
        stderr = io.StringIO()
        with self.assertRaises(SystemExit) as ctx, patch("sys.stderr", stderr):
            main(["query", "openclaw", "--limit", "0"])

        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("must be greater than 0", stderr.getvalue())

    def test_source_must_be_supported(self) -> None:
        stderr = io.StringIO()
        with self.assertRaises(SystemExit) as ctx, patch("sys.stderr", stderr):
            main(["search", "openclaw", "--source", "bing"])

        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("unsupported source 'bing'", stderr.getvalue())


class SearchAggregationTest(unittest.TestCase):
    def test_run_search_deduplicates_by_normalized_url_and_combines_sources(self) -> None:
        duckduckgo = _NamedSearchAdapter(
            "duckduckgo_html",
            [
                SearchResult(
                    title="OpenClaw",
                    url="https://example.com/openclaw/",
                    snippet="DuckDuckGo snippet",
                    source="duckduckgo_html",
                    rank=1,
                ),
                SearchResult(
                    title="Another result",
                    url="https://example.com/other",
                    snippet="Other result",
                    source="duckduckgo_html",
                    rank=2,
                ),
            ],
        )
        wikipedia = _NamedSearchAdapter(
            "wikipedia",
            [
                SearchResult(
                    title="OpenClaw",
                    url="https://example.com/openclaw",
                    snippet="Wikipedia snippet is a bit longer",
                    source="wikipedia",
                    rank=1,
                )
            ],
        )

        results = run_search([duckduckgo, wikipedia], query="openclaw", limit=5)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].normalized_url, "https://example.com/openclaw")
        self.assertEqual(results[0].sources, ("duckduckgo_html", "wikipedia"))
        self.assertEqual(results[0].source_ranks, {"duckduckgo_html": 1, "wikipedia": 1})
        self.assertEqual(results[0].snippet, "Wikipedia snippet is a bit longer")
        self.assertGreater(results[0].score, results[1].score)
        self.assertEqual(results[0].rank, 1)

    def test_run_search_uses_lightweight_ranking_to_prefer_cross_source_consensus(self) -> None:
        consensus_a = _NamedSearchAdapter(
            "duckduckgo_html",
            [
                SearchResult(
                    title="Consensus",
                    url="https://example.com/a",
                    snippet="Seen in source A",
                    source="duckduckgo_html",
                    rank=3,
                )
            ],
        )
        consensus_b = _NamedSearchAdapter(
            "wikipedia",
            [
                SearchResult(
                    title="Consensus",
                    url="https://example.com/a",
                    snippet="Seen in source B",
                    source="wikipedia",
                    rank=3,
                ),
                SearchResult(
                    title="Solo result",
                    url="https://example.com/b",
                    snippet="Only one source but ranked first",
                    source="wikipedia",
                    rank=1,
                ),
            ],
        )

        results = run_search([consensus_a, consensus_b], query="openclaw", limit=5)

        self.assertEqual(results[0].normalized_url, "https://example.com/a")
        self.assertEqual(results[1].normalized_url, "https://example.com/b")


class HTMLContentExtractorTest(unittest.TestCase):
    def test_extracts_title_excerpt_and_body_text(self) -> None:
        html = """
        <html>
          <head>
            <title>Example Page</title>
            <meta name="description" content="Short summary for preview." />
            <style>.hidden { display: none; }</style>
          </head>
          <body>
            <nav>Top navigation link</nav>
            <main>
              <h1>OpenClaw</h1>
              <p>Build your own search stack.</p>
              <script>console.log("ignored")</script>
            </main>
            <footer>Footer links</footer>
          </body>
        </html>
        """

        document = HTMLContentExtractor().extract(
            html,
            url="https://example.com",
            status_code=200,
        )

        self.assertEqual(document.title, "Example Page")
        self.assertEqual(document.url, "https://example.com/")
        self.assertEqual(document.final_url, "https://example.com/")
        self.assertEqual(document.excerpt, "Short summary for preview.")
        self.assertIn("OpenClaw Build your own search stack.", document.content)
        self.assertNotIn("ignored", document.content)
        self.assertNotIn("Top navigation", document.content)
        self.assertNotIn("Footer links", document.content)
        self.assertEqual(document.content_type, "text/html")

    def test_falls_back_to_h1_when_title_missing(self) -> None:
        html = """
        <html>
          <body>
            <main>
              <h1>Fallback Title</h1>
              <p>Useful content for the document body.</p>
            </main>
          </body>
        </html>
        """

        document = HTMLContentExtractor().extract(
            html,
            url="https://example.com/docs",
            status_code=200,
        )

        self.assertEqual(document.title, "Fallback Title")
        self.assertIn("Useful content", document.content)


class WikipediaSearchAdapterTest(unittest.TestCase):
    def test_search_normalizes_mediawiki_results(self) -> None:
        payload = {
            "query": {
                "search": [
                    {
                        "title": "OpenClaw",
                        "snippet": 'Local <span class="searchmatch">search</span> stack',
                    },
                    {
                        "title": "OpenClaw Engine",
                        "snippet": "Second result",
                    },
                ]
            }
        }

        class _FakeResponse:
            def __enter__(self) -> "_FakeResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(payload).encode("utf-8")

        with patch("searchstack.adapters.wikipedia.urlopen", return_value=_FakeResponse()) as mocked:
            results = WikipediaSearchAdapter().search("openclaw", limit=2)

        request = mocked.call_args.args[0]
        self.assertIn("srsearch=openclaw", request.full_url)
        self.assertIn("srlimit=2", request.full_url)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].title, "OpenClaw")
        self.assertEqual(results[0].snippet, "Local search stack")
        self.assertEqual(results[0].url, "https://en.wikipedia.org/wiki/OpenClaw")
        self.assertEqual(results[0].source, "wikipedia")
        self.assertEqual(results[0].rank, 1)
