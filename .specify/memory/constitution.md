# self-built-search Constitution

## Core Principles

### I. Local-First, Low-Cost by Default
This project exists to provide web discovery and retrieval without depending on paid search APIs in its core path. The default design must prefer local execution, free/public search sources, and self-hostable backends where practical.

### II. Adapter-Driven Architecture
Search sources, fetchers, extractors, and future backends must be modular adapters behind stable internal interfaces. No feature may hard-wire the entire project to a single provider or HTML structure without a clear abstraction boundary.

### III. Deterministic CLI and Structured Output
Every core capability must be accessible through a Python CLI. Commands must support structured machine-readable output first (JSON), with human-readable output as an optional layer. Errors must be explicit and actionable.

### IV. Retrieval Before Reasoning
The system must separate discovery, retrieval, extraction, and summarization into distinct stages. Search results are not facts; page retrieval and extraction are required before strong claims or summaries are emitted.

### V. Simplicity First, Then Expansion
Version 1 must stay narrow: query -> search -> normalize -> fetch. New providers, reranking, caching, and local indexing are welcome only after the base pipeline is stable, testable, and documented.

## Technical Constraints

- Primary implementation language: Python.
- Initial search source: DuckDuckGo HTML.
- Initial output contract: normalized JSON result objects.
- The codebase must remain ready for future SearXNG integration without requiring a rewrite of the core schema or CLI.
- Paid API dependencies are prohibited in the V1 critical path.

## Development Workflow

- Spec Kit is the governing workflow for this repository.
- Work should proceed in this order: constitution -> specify -> plan -> tasks -> implementation.
- Codex CLI is the preferred implementation agent for executing approved plans.
- Changes to schemas, CLI contracts, or adapter interfaces must be reflected in docs.

## Governance

This constitution supersedes ad-hoc implementation decisions. Any change that increases dependency cost, weakens modularity, or bypasses structured output must be justified in the spec or plan artifacts.

**Version**: 1.0.0 | **Ratified**: 2026-03-11 | **Last Amended**: 2026-03-11
