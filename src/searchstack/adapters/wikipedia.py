from __future__ import annotations

import json
import re
from html import unescape
from urllib.parse import quote
from urllib.request import Request, urlopen

from searchstack.models import SearchResult

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean_snippet(value: str) -> str:
    without_tags = _TAG_RE.sub(" ", value)
    return _WHITESPACE_RE.sub(" ", unescape(without_tags)).strip()


class WikipediaSearchAdapter:
    source_name = "wikipedia"
    search_url = "https://en.wikipedia.org/w/api.php"
    page_url_prefix = "https://en.wikipedia.org/wiki/"
    user_agent = "searchstack/0.1 (+https://example.invalid/local-first-search)"

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        request = Request(
            (
                f"{self.search_url}?"
                "action=query&list=search&format=json&utf8=1"
                f"&srlimit={limit}&srsearch={quote(query)}"
            ),
            headers={"User-Agent": self.user_agent},
        )
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        results: list[SearchResult] = []
        for index, item in enumerate(payload.get("query", {}).get("search", []), start=1):
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            results.append(
                SearchResult(
                    title=title,
                    url=f"{self.page_url_prefix}{quote(title.replace(' ', '_'))}",
                    snippet=_clean_snippet(str(item.get("snippet", ""))),
                    source=self.source_name,
                    rank=index,
                )
            )
        return results
