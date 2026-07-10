---
type: reference-synthesis
source: docs/08-References/raw/README.md
provenance: "Defines the contract for the immutable Layer-1 raw-sources directory of the vault ingestion pipeline, so downstream Layer-2 page generation has a stable, deduplicated source registry to read from."
---

## What it is

The specification for `docs/08-References/raw/`, the immutable Layer 1 raw-sources registry of the vault ingestion pipeline — a single append-only JSONL index of every source ever ingested, written exclusively by `lib/wiki_ingester.py`.

## Key mechanics

- **Single file**: `index.jsonl`, an append-only JSONL log with one JSON object per ingested source. No file in this directory is hand-edited.
- **Schema per line**: `source_id` (deterministic SHA-256-derived ID), `type` (`url`|`file`|`text`), `locator` (original URL, file path, or `"inline"`), `sha256_hash` (hex-64 hash of the raw body), `page_path` (the compiled Layer 2 output path, `docs/04-Concepts/ingested/<slug>.md`), `ingested_at` (ISO-8601 UTC timestamp).
- **Invariants**: `index.jsonl` is append-only (existing lines never mutated); `source_id` is stable across re-ingestion of identical content; re-ingesting a known `sha256_hash` returns the existing entry rather than adding a duplicate line (content-addressed dedup).
- **Two-layer pipeline**: Layer 1 (`docs/08-References/raw/index.jsonl`, immutable source registry) feeds Layer 2 (`docs/04-Concepts/ingested/<slug>.md`, compiled structured vault pages), with generation performed by `cos_lib.wiki_ingester.WikiIngester`.

## Relations & where used

Consumed exclusively by `lib/wiki_ingester.py` / `cos_lib.wiki_ingester.WikiIngester`, which both writes new entries to `index.jsonl` and generates the corresponding Layer 2 pages under `docs/04-Concepts/ingested/`.

## Status / caveats

This is a short, self-contained infrastructure spec rather than an index/MOC of external links — it documents a data contract (schema + invariants) for a pipeline component, so it was synthesized rather than skipped. No dated snapshot or inconsistency was found in the source; it describes durable structural rules, not point-in-time state.
