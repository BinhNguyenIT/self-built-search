from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from searchstack.models import SearchResult


def _clean_text(value: str) -> str:
    return " ".join(unescape(value).split())


def _unwrap_duckduckgo_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        uddg = parse_qs(parsed.query).get("uddg")
        if uddg:
            return uddg[0]
    return url


def _is_organic_result(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path in {"/y.js", "/html/"}:
        return False
    return True


@dataclass
class _PendingResult:
    title_parts: list[str] = field(default_factory=list)
    snippet_parts: list[str] = field(default_factory=list)
    url: str = ""

    def build(self, rank: int, source: str) -> SearchResult | None:
        title = _clean_text("".join(self.title_parts))
        snippet = _clean_text("".join(self.snippet_parts))
        url = _unwrap_duckduckgo_url(self.url.strip())
        if not title or not url or not _is_organic_result(url):
            return None
        return SearchResult(
            title=title,
            url=url,
            snippet=snippet,
            source=source,
            rank=rank,
        )


class _DuckDuckGoHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._results: list[_PendingResult] = []
        self._current: _PendingResult | None = None
        self._anchor_depth = 0
        self._snippet_depth = 0

    @property
    def results(self) -> list[_PendingResult]:
        return self._results

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        classes = set((attr_map.get("class") or "").split())

        if tag == "a" and "result__a" in classes:
            self._current = _PendingResult(url=attr_map.get("href") or "")
            self._anchor_depth = 1
            return

        if self._current and self._anchor_depth and tag == "a":
            self._anchor_depth += 1
            return

        if self._current and tag in {"a", "div"} and "result__snippet" in classes:
            self._snippet_depth = 1
            return

        if self._current and self._snippet_depth and tag in {"span", "b", "a", "div"}:
            self._snippet_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._anchor_depth and tag == "a":
            self._anchor_depth -= 1
            if self._anchor_depth == 0 and self._current:
                self._results.append(self._current)
            return

        if self._snippet_depth and tag in {"span", "b", "a", "div"}:
            self._snippet_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._current:
            return
        if self._anchor_depth:
            self._current.title_parts.append(data)
        elif self._snippet_depth:
            self._current.snippet_parts.append(data)


class DuckDuckGoHTMLAdapter:
    source_name = "duckduckgo_html"
    search_url = "https://html.duckduckgo.com/html/"
    user_agent = "searchstack/0.1 (+https://example.invalid/local-first-search)"

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        request = Request(
            f"{self.search_url}?{urlencode({'q': query})}",
            headers={"User-Agent": self.user_agent},
        )
        with urlopen(request, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")

        parser = _DuckDuckGoHTMLParser()
        parser.feed(html)

        results: list[SearchResult] = []
        for pending in parser.results:
            built = pending.build(rank=len(results) + 1, source=self.source_name)
            if built is None:
                continue
            results.append(built)
            if len(results) >= limit:
                break
        return results
