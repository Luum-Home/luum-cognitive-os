<!-- SCOPE: both -->
---
name: wiki-ingest
version: 0.1.0
description: Use when raw URLs, files, or pasted text need to be ingested into the compiled docs vault with raw-source indexing
  and optional Engram claim capture.
audience: both
tags:
- knowledge-architecture
- ingestion
- docs
- engram
triggers:
- wiki-ingest
- ingest raw source
- compile source into vault
related_adr: ADR-289
routing_intents:
- intent: wiki_ingest_source
  description: User wants to ingest a URL, file, or pasted source into the docs vault with raw-source indexing and optional
    memory capture.
  confidence: 0.84
---

# Wiki Ingest

Use this skill when a raw source needs to become a structured vault page under
`docs/04-Concepts/ingested/` and a raw-source index entry under
`docs/08-References/raw/index.jsonl`.

## Procedure

1. Confirm the source type: URL, local file, or inline pasted text.
2. Use `lib.wiki_ingester.WikiIngester` from the repository root.
3. Call the matching method: `ingest_url`, `ingest_file`, or `ingest_text`.
4. Review the generated page and the appended raw index row.
5. Run the relevant focused tests or audits for the touched docs surface.

## Python example

```python
from pathlib import Path
from lib.wiki_ingester import WikiIngester

ingester = WikiIngester(Path.cwd())
result = ingester.ingest_text("Source title", "Source body")
print(result.source_id, result.page_path)
```

## Guarantees

- Secrets matching the conservative redaction pattern are replaced before the
  vault page is written.
- Re-ingesting the same body returns the existing source id instead of appending
  duplicate index rows.
- Engram capture is best-effort; ingestion still succeeds when Engram is not
  available.

## Contextual Trigger

Use this when prompts mention raw-source ingestion, wiki ingestion, compiled
vault pages, or Layer 1 to Layer 2 movement from ADR-289.
