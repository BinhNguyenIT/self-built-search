from __future__ import annotations

from dataclasses import asdict, dataclass, field

from searchstack.utils import normalize_url


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    rank: int
    normalized_url: str = ""
    score: float = 0.0
    sources: tuple[str, ...] = ()
    source_ranks: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["normalized_url"] = self.normalized_url or normalize_url(self.url)
        payload["score"] = round(self.score, 6)
        payload["sources"] = list(self.sources or (self.source,))
        payload["source_ranks"] = dict(self.source_ranks or {self.source: self.rank})
        return payload


@dataclass(slots=True)
class FetchedDocument:
    url: str
    final_url: str
    title: str
    excerpt: str
    content: str
    status_code: int | None
    content_type: str
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class QueryResult:
    rank: int
    source: str
    score: float
    sources: tuple[str, ...]
    search: SearchResult
    document: FetchedDocument

    def to_dict(self) -> dict[str, object]:
        return {
            "rank": self.rank,
            "source": self.source,
            "score": round(self.score, 6),
            "sources": list(self.sources),
            "search": self.search.to_dict(),
            "document": self.document.to_dict(),
        }
