from __future__ import annotations

from dataclasses import dataclass, field

from searchstack.adapters.base import FetchAdapter, SearchAdapter
from searchstack.models import FetchedDocument, QueryResult, SearchResult
from searchstack.utils import normalize_url


@dataclass(slots=True)
class _AggregateCandidate:
    normalized_url: str
    title: str = ""
    snippet: str = ""
    source_ranks: dict[str, int] = field(default_factory=dict)
    source_order: dict[str, int] = field(default_factory=dict)
    raw_url_by_source: dict[str, str] = field(default_factory=dict)
    score: float = 0.0

    def absorb(self, result: SearchResult, source_index: int) -> None:
        self.source_order.setdefault(result.source, source_index)
        existing_rank = self.source_ranks.get(result.source)
        if existing_rank is not None and existing_rank <= result.rank:
            return

        self.source_ranks[result.source] = result.rank
        self.raw_url_by_source[result.source] = result.url
        self.score = sum(1.0 / (60 + rank) for rank in self.source_ranks.values())

        if not self.title or (result.title and len(result.title) > len(self.title)):
            self.title = result.title
        if not self.snippet or (result.snippet and len(result.snippet) > len(self.snippet)):
            self.snippet = result.snippet

    def build(self) -> SearchResult:
        ordered_sources = tuple(
            sorted(
                self.source_ranks,
                key=lambda source: (self.source_ranks[source], self.source_order[source], source),
            )
        )
        primary_source = ordered_sources[0]
        return SearchResult(
            title=self.title,
            url=self.raw_url_by_source[primary_source],
            snippet=self.snippet,
            source=primary_source,
            rank=0,
            normalized_url=self.normalized_url,
            score=self.score,
            sources=ordered_sources,
            source_ranks={source: self.source_ranks[source] for source in ordered_sources},
        )


def run_search(adapters: list[SearchAdapter], query: str, limit: int) -> list[SearchResult]:
    candidates: dict[str, _AggregateCandidate] = {}

    for source_index, adapter in enumerate(adapters):
        for result in adapter.search(query, limit=limit):
            normalized = normalize_url(result.url)
            candidate = candidates.setdefault(
                normalized,
                _AggregateCandidate(normalized_url=normalized),
            )
            candidate.absorb(result, source_index=source_index)

    ordered_results = sorted(
        (candidate.build() for candidate in candidates.values()),
        key=lambda result: (
            -result.score,
            min(result.source_ranks.values()),
            len(result.sources),
            result.source,
            result.normalized_url,
        ),
    )

    for index, result in enumerate(ordered_results[:limit], start=1):
        result.rank = index

    return ordered_results[:limit]


def run_fetch(adapter: FetchAdapter, url: str) -> FetchedDocument:
    return adapter.fetch(url)


def run_query(
    search_adapters: list[SearchAdapter],
    fetch_adapter: FetchAdapter,
    query: str,
    limit: int,
) -> list[QueryResult]:
    search_results = run_search(search_adapters, query=query, limit=limit)
    query_results: list[QueryResult] = []
    for result in search_results:
        try:
            document = run_fetch(fetch_adapter, url=result.url)
        except Exception as exc:
            document = FetchedDocument(
                url=result.url,
                final_url=result.url,
                title="",
                excerpt="",
                content="",
                status_code=None,
                content_type="",
                error=f"{exc.__class__.__name__}: {exc}",
            )
        query_results.append(
            QueryResult(
                rank=result.rank,
                source=result.source,
                score=result.score,
                sources=result.sources or (result.source,),
                search=result,
                document=document,
            )
        )
    return query_results
