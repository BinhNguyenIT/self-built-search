from __future__ import annotations

from typing import Protocol

from searchstack.models import FetchedDocument, SearchResult


class SearchAdapter(Protocol):
    source_name: str

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        ...


class FetchAdapter(Protocol):
    def fetch(self, url: str) -> FetchedDocument:
        ...
