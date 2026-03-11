# Architecture

## Problem

Need a cheap, owned web discovery layer for agent workflows.

## Recommended MVP

1. Query input
2. Search adapters (`duckduckgo`, `wikipedia`, or both)
3. Result aggregation with normalized-URL dedupe
4. Lightweight ordering that preserves source rank plus cross-source agreement
5. URL fetch adapter
6. HTML/text extraction
7. Stable JSON output layer for agents and shell use

## Future evolution

- More adapters
- Cache/index
- SearXNG backend option
- OpenClaw skill wrapper
