from __future__ import annotations

import argparse
import json
import sys

from searchstack.adapters import (
    DuckDuckGoHTMLAdapter,
    URLFetchAdapter,
    WikipediaSearchAdapter,
)
from searchstack.services import run_fetch, run_query, run_search


SEARCH_SOURCES = ("duckduckgo", "wikipedia")


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def _parse_sources(value: str) -> tuple[str, ...]:
    raw = value.strip().lower()
    if raw == "all":
        return SEARCH_SOURCES

    selected: list[str] = []
    for item in raw.split(","):
        source = item.strip()
        if not source:
            continue
        if source not in SEARCH_SOURCES:
            allowed = ", ".join((*SEARCH_SOURCES, "all"))
            raise argparse.ArgumentTypeError(f"unsupported source '{source}'; expected one of: {allowed}")
        if source not in selected:
            selected.append(source)

    if not selected:
        raise argparse.ArgumentTypeError("source selection cannot be empty")
    return tuple(selected)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="searchstack",
        description="Local-first web discovery CLI.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    search_parser = subcommands.add_parser(
        "search",
        help="Search a configured source and print normalized JSON results.",
    )
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--limit",
        type=_positive_int,
        default=5,
        help="Maximum number of results to return",
    )
    search_parser.add_argument(
        "--source",
        type=_parse_sources,
        default=("duckduckgo",),
        help="Search source(s) to use: duckduckgo, wikipedia, comma-separated list, or all",
    )

    fetch_parser = subcommands.add_parser(
        "fetch",
        help="Fetch a URL and print normalized JSON content.",
    )
    fetch_parser.add_argument("url", help="URL to fetch")

    query_parser = subcommands.add_parser(
        "query",
        help="Search then fetch the top normalized results.",
    )
    query_parser.add_argument("query", help="Search query")
    query_parser.add_argument(
        "--limit",
        type=_positive_int,
        default=3,
        help="Maximum number of results to search and fetch",
    )
    query_parser.add_argument(
        "--source",
        type=_parse_sources,
        default=("duckduckgo",),
        help="Search source(s) to use: duckduckgo, wikipedia, comma-separated list, or all",
    )
    return parser


def create_search_adapters(sources: tuple[str, ...] = ("duckduckgo",)) -> list[DuckDuckGoHTMLAdapter | WikipediaSearchAdapter]:
    adapters: list[DuckDuckGoHTMLAdapter | WikipediaSearchAdapter] = []
    for source in sources:
        if source == "duckduckgo":
            adapters.append(DuckDuckGoHTMLAdapter())
            continue
        if source == "wikipedia":
            adapters.append(WikipediaSearchAdapter())
            continue
        raise ValueError(f"unsupported search source: {source}")
    return adapters


def create_fetch_adapter() -> URLFetchAdapter:
    return URLFetchAdapter()


def _print_error(exc: Exception) -> int:
    print(
        json.dumps(
            {
                "error": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                }
            }
        ),
        file=sys.stderr,
    )
    return 1


def _search_payload(
    *,
    query: str,
    sources: tuple[str, ...],
    limit: int,
    results: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "query": query,
        "sources": list(sources),
        "limit": limit,
        "result_count": len(results),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "search":
        try:
            results = run_search(
                create_search_adapters(args.source),
                query=args.query,
                limit=args.limit,
            )
        except Exception as exc:
            return _print_error(exc)

        print(
            json.dumps(
                _search_payload(
                    query=args.query,
                    sources=args.source,
                    limit=args.limit,
                    results=[result.to_dict() for result in results],
                ),
                indent=2,
            )
        )
        return 0

    if args.command == "fetch":
        try:
            document = run_fetch(create_fetch_adapter(), url=args.url)
        except Exception as exc:
            return _print_error(exc)

        print(
            json.dumps(
                {
                    "url": args.url,
                    "document": document.to_dict(),
                },
                indent=2,
            )
        )
        return 0

    if args.command == "query":
        try:
            results = run_query(
                create_search_adapters(args.source),
                create_fetch_adapter(),
                query=args.query,
                limit=args.limit,
            )
        except Exception as exc:
            return _print_error(exc)

        print(
            json.dumps(
                _search_payload(
                    query=args.query,
                    sources=args.source,
                    limit=args.limit,
                    results=[result.to_dict() for result in results],
                ),
                indent=2,
            )
        )
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
