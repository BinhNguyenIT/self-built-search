"""Search adapters."""

from .duckduckgo import DuckDuckGoHTMLAdapter
from .fetch import HTMLContentExtractor, URLFetchAdapter
from .wikipedia import WikipediaSearchAdapter

__all__ = [
    "DuckDuckGoHTMLAdapter",
    "HTMLContentExtractor",
    "URLFetchAdapter",
    "WikipediaSearchAdapter",
]
