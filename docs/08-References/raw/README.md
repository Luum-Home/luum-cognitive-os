# Layer 1 — Raw Sources

This directory is the **immutable raw-sources layer** of the vault ingestion pipeline.

## Purpose

`docs/08-References/raw/` holds the persistent index of every source that has been
ingested into the compiled vault.  Nothing here is edited by hand; all writes are
performed by `lib/wiki_ingester.py`.

## Files

| File | Description |
|------|-------------|
| `index.jsonl` | Append-only JSONL log; one JSON object per ingested source. |

## index.jsonl schema

Each line is a valid JSON object with the following fields:

```jsonc
{
  "source_id":   "sha256-abc123",   // deterministic ID derived from SHA-256 hash
  "type":        "url|file|text",   // input modality
  "locator":     "https://…",       // original URL, file path, or "inline"
  "sha256_hash": "abc123…",         // SHA-256 of the raw body (hex, 64 chars)
  "page_path":   "docs/04-Concepts/ingested/<slug>.md",  // compiled output
  "ingested_at": "2026-05-13T00:00:00Z"  // ISO-8601 UTC
}
```

## Invariants

- `index.jsonl` is **append-only** — existing lines are never mutated.
- `source_id` is stable across re-ingestion of the same content.
- Re-ingesting an already-known `sha256_hash` returns the existing entry without
  adding a duplicate line.

## Layer relationship

```
Layer 1: docs/08-References/raw/index.jsonl   ← immutable source registry
Layer 2: docs/04-Concepts/ingested/<slug>.md  ← compiled, structured vault pages
```

Layer 2 pages are generated from Layer 1 sources by `lib.wiki_ingester.WikiIngester`.
