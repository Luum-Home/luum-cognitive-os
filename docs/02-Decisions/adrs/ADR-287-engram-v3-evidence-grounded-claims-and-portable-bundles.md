---
adr: 287
title: 'Engram v3: Evidence-Grounded Claims, Write Gate, BM25 Retrieval Wrapper, and Portable Bundles'
status: accepted
implementation_status: implemented
date: '2026-05-13'
supersedes: []
superseded_by: null
implementation_files:
  - lib/engram_wave3_schema.py
  - lib/engram_write_gate.py
  - lib/engram_fts5_search.py
  - lib/engram_bundle_exporter.py
  - lib/engram_bundle_importer.py
tier: maintainer
tags:
  - engram
  - schema
  - retrieval
  - portability
classification_basis: engram v3 schema migration, write-gate dry-run wrapper, BM25 retrieval, and bundle export/import all implemented with executing unit tests
verification:
  level: strong
  commands:
  - python3 -m pytest tests/unit/test_engram_wave3_schema.py tests/unit/test_engram_write_gate.py tests/unit/test_engram_fts5_search.py tests/unit/test_engram_bundle_roundtrip.py -q
  proves:
  - schema_migration_idempotent
  - evidence_hash_deterministic
  - write_gate_dry_run_returns_preview
  - bm25_ranking_present
  - bundle_export_import_roundtrip
---

# ADR-287 — Engram v3: Evidence-Grounded Claims, Write Gate, BM25 Retrieval Wrapper, and Portable Bundles

## Status

Accepted

**Date:** 2026-05-13
**Owner:** orchestrator
**Tier:** core
**Authors:** orchestrator
**Related:** ADR-261 (memory governance v2), Engram Wave 2 schema (`lib/engram_wave2_schema.py`)

---

## Context

### Current state of engram (post Wave 2)

Engram is a local SQLite-backed observation store with an HTTP daemon at port
`7437` and a thin CLI. Wave 2 (`lib/engram_wave2_schema.py`) added temporal
validity (`valid_from`, `valid_to`), a `memory_class` field, and a
`source_episode` pointer in an additive, idempotent migration. The `observations`
table already has an FTS5 mirror (`observations_fts`) with `INSERT`/`UPDATE`/`DELETE`
triggers that keep the index in sync.

The `memory_relations` table holds judgment edges between observations and
already carries an `evidence TEXT` column and a `confidence REAL` column used by
the conflict-surfacing protocol (`mem_judge`).

### Four gaps observed in real use

1. **Claims without traceable evidence.** `mem_save` accepts arbitrary
   `content` strings. Observations of type `fact`, `decision`, or `workflow`
   frequently encode load-bearing claims (file paths, configuration values,
   architectural rules). Today nothing prevents an agent from persisting a
   fabricated claim, and there is no machine-checkable link from the claim back
   to the artifact(s) that justified it. The free-text `evidence` column on
   `memory_relations` is per-edge, not per-observation, and is not
   content-hashed, so we cannot detect drift if the source artifact later
   changes.
2. **Writes commit immediately, with no review surface.** Every `mem_save` is
   irrevocable in the sense that the only "preview" today is for the caller to
   build the payload manually before calling. There is no `dry_run` mode that
   returns the exact record that *would* be written, and no opt-in strict mode
   that requires explicit approval before commit. For high-blast-radius writes
   (e.g. architecture decisions) this asymmetry matters.
3. **Retrieval ranking is opaque to callers.** `observations_fts` exists and
   supports BM25, but `lib.engram_client.search_observations` and the HTTP
   daemon's `/observations/search` endpoint do not surface the BM25 score nor a
   snippet. Callers cannot reason about *why* a hit ranked above another, and
   cannot ask for ordered top-K by BM25 directly from Python without bypassing
   the daemon.
4. **No portable cross-instance handoff.** Memory is bound to the local
   `~/.engram/engram.db`. When a workstation is reimaged, or when work needs to
   move between machines, there is no canonical, integrity-checked export of a
   scoped slice of memory. Today the only options are full SQLite copy (too
   coarse) or Obsidian export (lossy, not re-importable).

### Investigation: what already exists

- **FTS5 + BM25:** already present. `observations_fts` is a contentless FTS5
  virtual table mirroring `observations(title, content, tool_name, type,
  project, topic_key)`. Triggers `obs_fts_insert/delete/update` keep it in
  sync. A direct `SELECT bm25(observations_fts), snippet(...) FROM
  observations_fts WHERE observations_fts MATCH ?` works today against the live
  DB. **Therefore v3 ships only a thin Python wrapper, not a new index.**
- **Wave 2 columns:** valid temporal scaffolding already present; v3 reuses the
  additive `ALTER TABLE ... ADD COLUMN` pattern for the new evidence columns.
- **`memory_relations.evidence`:** free-text only, per-edge. v3 adds a
  structured per-observation evidence mechanism rather than overloading the
  edge field.

---

## Decision

Ship four orthogonal capabilities under the umbrella name **Engram v3**, each
implemented as an additive Python module that can be adopted incrementally
without breaking the v2 surface.

### 1. Evidence-grounded claims (schema v3)

Add two nullable columns to `observations`:

- `evidence_sources TEXT` — JSON-encoded list of source IDs.
- `evidence_hashes TEXT` — JSON-encoded `{source_id: sha256}` map captured at
  claim-write time.

Add a new table `evidence_sources` with `(id TEXT PRIMARY KEY, type TEXT,
locator TEXT, sha256_hash TEXT, created_at TEXT, metadata TEXT)`. Sources are
de-duplicated by `id` (a stable hash of `type:locator`). A validator function
`validate_claim_evidence(obs_type, evidence)` enforces non-empty evidence for
the claim-bearing types (`fact`, `decision`, `workflow`) and a permissive
policy for narrative types (`discovery`, `bugfix`, `note`, `manual`).

`compute_source_hash(locator, type_)` is a deterministic function:
- For `file://` and bare paths: streaming SHA-256 of file bytes.
- For `url://`, `transcript://`, `conversation://`: SHA-256 of the resolved
  body text.

### 2. Dry-run / approved write gate

A new `lib/engram_write_gate.py` wraps any save callable
(`save_fn: Callable[..., dict|None]`) with two parameters:

- `dry_run: bool = False` — when true, returns a `WriteGatePreview` dict with
  the exact payload that would be written, the resolved topic key, and (if
  applicable) the existing observation that would be updated. **No DB write
  occurs.**
- `approved: bool = True` — defaults true for backwards compatibility. When
  `ENGRAM_REQUIRE_APPROVAL=1` is set in the environment, `approved=False`
  rejects the call with a clear `ApprovalRequiredError`.

Every gated call emits a JSONL audit line to
`.cognitive-os/metrics/engram-write-gate.jsonl` with timestamp, action
(`dry_run | approved | rejected`), title, topic_key, evidence count, and
caller-supplied actor.

### 3. BM25 retrieval wrapper

A new `lib/engram_fts5_search.py` exposes:

```python
def search_bm25(query: str, *, db_path: str|Path = DEFAULT_DB,
                limit: int = 10, project: str|None = None,
                type_filter: str|None = None,
                snippet_chars: int = 24) -> list[BM25Hit]
```

`BM25Hit` carries `(observation_id, title, snippet, score, project, type)`.
The wrapper opens the SQLite DB read-only (`mode=ro` URI), runs a parameterized
`MATCH` query against the existing `observations_fts`, applies
`bm25(observations_fts)` for ordering, and uses `snippet(observations_fts, 1,
'[', ']', '...', N)` for the content column. **No schema changes** — this
module is a read-only wrapper over the index that already exists.

### 4. Portable bundle export/import

Two modules:

- `lib/engram_bundle_exporter.py:export(target_dir, *, scope_filter, since,
  db_path)` writes:
  - `bundle/manifest.json` — schema version, counts per stream, per-file
    SHA-256, overall `bundle_sha256` over the concatenation of file hashes.
  - `bundle/claims.jsonl` — one observation per line, v3 fields included.
  - `bundle/sources.jsonl` — referenced `evidence_sources` rows.
  - `bundle/relations.jsonl` — referenced `memory_relations` rows.
- `lib/engram_bundle_importer.py:import_bundle(bundle_path, *,
  dry_run=True)` verifies all file hashes against the manifest, rejects
  on schema-version mismatch, returns a conflict report. `apply_bundle(...)`
  performs the insert (with `INSERT OR IGNORE` on `sync_id`) only when
  `approved=True`.

---

## Schema diff (v2 → v3)

```
observations:
  + evidence_sources TEXT   (nullable, JSON list of source IDs)
  + evidence_hashes  TEXT   (nullable, JSON map source_id->sha256)

new table evidence_sources:
  id          TEXT PRIMARY KEY  -- sha256(type ':' locator) [16 hex chars]
  type        TEXT NOT NULL     -- file|url|transcript|conversation
  locator     TEXT NOT NULL
  sha256_hash TEXT              -- content hash at registration time
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
  metadata    TEXT              -- JSON, optional
```

The migration is gated by `ensure_wave3_schema(db_path, dry_run=False)` which:
1. `ALTER TABLE observations ADD COLUMN evidence_sources TEXT` (if missing).
2. `ALTER TABLE observations ADD COLUMN evidence_hashes TEXT` (if missing).
3. `CREATE TABLE IF NOT EXISTS evidence_sources (...)`.
4. `CREATE INDEX IF NOT EXISTS idx_evidence_sources_type ON evidence_sources(type)`.

Idempotent. Same pattern as `ensure_wave2_schema`.

---

## Migration plan v2 → v3

1. **Phase A (additive, zero-downtime):** run `ensure_wave3_schema` on the live
   DB. Existing rows have `evidence_sources = NULL` and remain valid.
2. **Phase B (opt-in writes):** new writes flowing through the write gate may
   attach evidence; old call sites continue to work unchanged.
3. **Phase C (strict mode, opt-in per environment):** set
   `ENGRAM_REQUIRE_EVIDENCE_FOR_TYPES=fact,decision,workflow` to make the
   write gate reject writes of those types without evidence. Off by default.
4. **Phase D (backfill, optional):** a future ADR may walk existing
   `fact|decision|workflow` rows and propose evidence where deterministic
   (e.g. an architecture observation referencing an ADR file gets that ADR
   registered as a source).

No phase requires destructive changes. Rollback = stop using the new modules;
columns remain NULL.

---

## Tradeoffs

| Concern | Impact |
| --- | --- |
| DB size | +2 nullable TEXT columns on `observations` + small new table. Negligible (<1% on a 6k-row DB). |
| Write latency | Evidence hash is streamed; for typical claim sources (<1 MB) the cost is sub-ms. URL/transcript hashing depends on caller. |
| Backwards compat | Fully additive. v2 callers see no behavior change. |
| Complexity | Four small modules, each independently testable. No shared mutable state. |
| Strict mode foot-gun | `ENGRAM_REQUIRE_APPROVAL=1` could block hooks unexpectedly. Mitigation: off by default; opt-in per environment. |

---

## Consequences

**Positive:**
- Claim-bearing observations can be cryptographically anchored to their
  sources; drift becomes detectable.
- Dry-run preview unblocks safe automation of high-blast-radius writes.
- BM25 retrieval becomes a first-class Python API surface, removing the need
  for callers to know SQL.
- Memory becomes portable across machines with integrity guarantees.

**Negative / accepted:**
- v3 modules add four files (~1k LOC total) to maintain.
- `evidence_sources` is per-observation; multi-observation claims share
  sources via shared source IDs but require callers to manage de-dup
  externally (the source table itself dedupes by `id`).

**Neutral:**
- FTS5 was already in use; v3 surfaces it but does not change indexing.

---

## Implementation files

- `lib/engram_wave3_schema.py` — additive migration + dataclasses + validators.
- `lib/engram_write_gate.py` — dry-run / approved wrapper + audit log.
- `lib/engram_fts5_search.py` — BM25 + snippet read-only wrapper.
- `lib/engram_bundle_exporter.py` — hashed JSONL bundle export.
- `lib/engram_bundle_importer.py` — verify + apply bundle.
- `tests/unit/test_engram_wave3_schema.py` — schema + hash + validator tests.
- `tests/unit/test_engram_write_gate.py` — dry-run, approval, audit.
- `tests/unit/test_engram_fts5_search.py` — BM25 ranking + snippet.
- `tests/unit/test_engram_bundle_roundtrip.py` — export/import roundtrip.

## Alternatives rejected

1. **Keep evidence as free text on `memory_relations` only.** Rejected because
   relation-level evidence does not anchor the observation itself and cannot
   detect source drift after the fact.
2. **Replace the existing FTS5 index.** Rejected because FTS5 and BM25 already
   exist in the live schema; v3 only needs a safe wrapper that exposes ranking
   and snippets.
3. **Export the whole SQLite database as the portability format.** Rejected
   because full DB copies are too broad, difficult to merge, and do not provide
   scoped conflict reports for cross-machine handoff.

## Verification

```bash
python3 -m pytest tests/unit/test_engram_wave3_schema.py tests/unit/test_engram_write_gate.py tests/unit/test_engram_fts5_search.py tests/unit/test_engram_bundle_roundtrip.py -q
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

These checks prove the schema migration is idempotent, evidence hashes are
stable, write-gate dry-run mode does not persist data, BM25 retrieval returns
ranked hits, bundle export/import validates hashes, and the ADR satisfies the
post-ADR-067 documentation contract.

---

## Relationship to ADR-289 (Three-Layer Knowledge Architecture)

ADR-289 names the durable knowledge model of the project as three layers —
raw sources (Layer 1), the compiled `docs/` vault (Layer 2), and operational
memory (Layer 3). **Engram v3 as specified here is the implementation of
Layer 3.** Every capability shipped under this ADR slots cleanly into that
model:

- `evidence_sources` rows and the `evidence_hashes` map on observations are
  the mechanical link from Layer 3 back to Layer 1 (raw files, URLs,
  transcripts) and to Layer 2 (vault pages addressed by their repo-relative
  paths). The deterministic `source_id = sha256(type ':' locator)[:16]` is
  the shared identity scheme across all three layers.
- The write gate is the enforcement point for the Layer 3 schema invariant
  defined by ADR-289: claim-bearing observation types
  (`fact | decision | workflow`) require at least one resolvable source in
  Layer 1 or Layer 2 when `ENGRAM_REQUIRE_EVIDENCE_FOR_TYPES` is set.
- Portable bundles are how Layer 3 moves between machines. ADR-289's
  `bundle` pipeline (L3 ↔ L3) is exactly the export/import surface defined
  in this ADR; the per-file SHA-256 and overall `bundle_sha256` provide the
  integrity guarantee Layer 3 needs to remain trustworthy after transit.
- The Obsidian export wrapper (already in tree as
  `lib/engram_obsidian_exporter.py`) is the `export` pipeline in ADR-289
  (L3 → L2). Bundle snapshots may therefore include or reference exported
  vault pages without breaking the layer model.

In short, ADR-287 defines *how* Layer 3 stores and proves its claims; ADR-289
defines *where* that layer sits in the broader knowledge architecture and
what its neighbors are.
