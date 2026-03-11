# self-built-search

A local-first web discovery stack for OpenClaw.

## Goal

Build an owned search orchestration stack instead of relying on paid search APIs.

## MVP status

This repo now includes a runnable Python MVP named `searchstack`:

- Python package under `src/searchstack`
- CLI entrypoints: `searchstack search`, `searchstack fetch`, `searchstack query`
- DuckDuckGo HTML adapter
- Wikipedia search adapter via the public MediaWiki API
- multi-source search selection (`duckduckgo`, `wikipedia`, comma-separated lists, or `all`)
- cross-source deduplication by normalized URL
- lightweight cross-source ranking that favors both strong placement and agreement across sources
- stdlib URL fetch adapter with basic HTML text extraction
- normalized JSON schemas for search results and fetched documents
- normalized fetch metadata (`final_url`, `content_type`) for agent use
- safer `query` behavior that preserves search hits even when one fetch fails
- tests for CLI envelopes, source selection, deduplication, ranking, and HTML extraction

The current scope is intentionally narrow: `search -> fetch -> normalize -> print JSON`.

## Run the MVP

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
searchstack search "open source search tools"
searchstack search "open source search tools" --source wikipedia
searchstack search "open source search tools" --source all
searchstack search "open source search tools" --source duckduckgo,wikipedia
searchstack fetch "https://example.com"
searchstack query "open source search tools" --source all --limit 3
```

You can also run it without installing the console script:

```bash
PYTHONPATH=src python3 -m searchstack search "open source search tools"
```

`search` and `query` accept `--source duckduckgo`, `--source wikipedia`, comma-separated combinations like `--source duckduckgo,wikipedia`, or `--source all`. The default remains `duckduckgo`.

Example output:

```json
{
  "query": "open source search tools",
  "sources": ["duckduckgo", "wikipedia"],
  "limit": 5,
  "result_count": 1,
  "results": [
    {
      "title": "Example title",
      "url": "https://example.com",
      "snippet": "Example snippet",
      "source": "duckduckgo_html",
      "sources": ["duckduckgo_html", "wikipedia"],
      "source_ranks": {
        "duckduckgo_html": 1,
        "wikipedia": 2
      },
      "normalized_url": "https://example.com",
      "score": 0.032522,
      "rank": 1
    }
  ]
}
```

`fetch` returns a stable document envelope:

```json
{
  "url": "https://example.com",
  "document": {
    "url": "https://example.com",
    "final_url": "https://example.com/",
    "title": "Example Domain",
    "excerpt": "Example preview text",
    "content": "Example page text",
    "status_code": 200,
    "content_type": "text/html",
    "error": ""
  }
}
```

`query` returns the same top-level envelope as `search`, with each result carrying both the aggregated search hit and fetched document. If a fetch fails, the item is still returned with an empty document body and an `error` string:

```json
{
  "query": "open source search tools",
  "sources": ["duckduckgo", "wikipedia"],
  "limit": 3,
  "result_count": 1,
  "results": [
    {
      "rank": 1,
      "source": "duckduckgo_html",
      "sources": ["duckduckgo_html", "wikipedia"],
      "score": 0.032522,
      "search": {
        "title": "Example title",
        "url": "https://example.com",
        "snippet": "Example snippet",
        "source": "duckduckgo_html",
        "sources": ["duckduckgo_html", "wikipedia"],
        "source_ranks": {
          "duckduckgo_html": 1,
          "wikipedia": 2
        },
        "normalized_url": "https://example.com",
        "score": 0.032522,
        "rank": 1
      },
      "document": {
        "url": "https://example.com",
        "final_url": "https://example.com/",
        "title": "Example Domain",
        "excerpt": "Example preview text",
        "content": "Example page text",
        "status_code": 200,
        "content_type": "text/html",
        "error": ""
      }
    }
  ]
}
```

## Test

Run the smoke test with the standard library test runner:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Planned architecture

- query interface
- source adapters
- source aggregation / ranking
- result normalization
- page retrieval
- summarization / reasoning
- optional cache/index layer

## Notes

This repo is meant to become the local search backend that OpenClaw can call without paid search APIs. The code stays adapter-driven and JSON-first so future search backends, fetchers, or a SearXNG layer can be added without rewriting the CLI contracts.
