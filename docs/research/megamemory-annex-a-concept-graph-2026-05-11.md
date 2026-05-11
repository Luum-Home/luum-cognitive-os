---
title: "MegaMemory Annex A — Concept Graph & Relation Model"
date: 2026-05-11
parent: docs/research/megamemory-comparison-2026-05-11.md
source-repo: ".cognitive-os/external-source-cache/MegaMemory (v1.6.2)"
---

> **License attribution.** Code excerpts and structural descriptions quoted from `0xK3vin/MegaMemory` v1.6.2 (MIT License, Copyright (c) 2026 0xk3vin — see https://github.com/0xK3vin/MegaMemory/blob/main/LICENSE). MIT permits direct vendoring with copyright preservation. See [`megamemory-annex-f-compliance-cleanroom-2026-05-11.md`](megamemory-annex-f-compliance-cleanroom-2026-05-11.md) for the full compliance protocol and port-vs-vendor decisions.

# Annex A — Concept Graph & Relation Model

Drills the data model: the 6 concept kinds, the 5 relation types, the SQLite v4 schema, and a side-by-side with Engram's `memory_relations` typed graph.

---

## 1. The schema, in MegaMemory's own words

### Node kinds (`src/types.ts:22-28`)

```ts
export type NodeKind =
  | "feature"
  | "module"
  | "pattern"
  | "config"
  | "decision"
  | "component";
```

Six fixed string-literal kinds. No subclasses, no dynamic kinds, no namespace per project. Enforced via `zod` enum at the MCP boundary (`src/index.ts:196-198`):

```ts
const NodeKindEnum = z.enum([
  "feature", "module", "pattern", "config", "decision", "component",
]);
```

### Relation types (`src/types.ts:43-48`)

```ts
export type RelationType =
  | "connects_to"
  | "depends_on"
  | "implements"
  | "calls"
  | "configured_by";
```

Five directed relations. No `supersedes`, no `conflicts_with`, no temporal validity, no judgment lifecycle. Edges are append-only, deduplicated by `(from_id, to_id, relation)` (unique index added in schema v4, `src/db.ts:166-169`).

### Node row layout (`src/db.ts:51-71`)

```sql
CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  summary TEXT NOT NULL,
  why TEXT,
  file_refs TEXT,                 -- JSON-encoded string[]
  parent_id TEXT,                 -- self-FK, hierarchical concepts
  created_by_task TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  removed_at TEXT,                -- soft-delete tombstone
  removed_reason TEXT,
  embedding BLOB,                 -- float32 buffer (384 floats = 1536 bytes)
  merge_group TEXT,               -- UUID grouping conflict siblings
  needs_merge INTEGER DEFAULT 0,
  source_branch TEXT,
  merge_timestamp TEXT,
  FOREIGN KEY (parent_id) REFERENCES nodes(id) ON DELETE SET NULL
);
```

### Edge row layout (`src/db.ts:73-86`)

```sql
CREATE TABLE IF NOT EXISTS edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_id TEXT NOT NULL,
  to_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  description TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  merge_group TEXT,
  needs_merge INTEGER DEFAULT 0,
  source_branch TEXT,
  merge_timestamp TEXT,
  FOREIGN KEY (from_id) REFERENCES nodes(id) ON DELETE CASCADE,
  FOREIGN KEY (to_id) REFERENCES nodes(id) ON DELETE CASCADE
);
```

### Migration chain (`src/db.ts:37-178`)

```
v1: nodes + edges + indices (kind / parent / removed)
v2: ALTER TABLE nodes/edges ADD merge_group, needs_merge, source_branch, merge_timestamp
v3: CREATE TABLE timeline (seq, timestamp, tool, params, result_summary,
                           is_write, is_error, affected_ids)
v4: DELETE duplicate edges + CREATE UNIQUE INDEX idx_edges_unique
                            ON edges(from_id, to_id, relation)
```

Migrations run inside `BEGIN IMMEDIATE` with a re-check after acquiring the write lock (`src/db.ts:42-49`), which is a competent multi-process safety pattern worth noting.

### Pragmas at open (`src/db.ts:20-23`)

```ts
this.db.pragma("journal_mode = WAL");
this.db.pragma("foreign_keys = ON");
this.db.pragma("busy_timeout = 5000");
this.db.pragma("synchronous = NORMAL");
```

Standard hardened-SQLite defaults. WAL, 5s busy retry, FK enforcement, NORMAL sync (durability vs throughput tradeoff sane for a per-project knowledge DB).

### ID convention (`src/tools.ts:33-41`)

IDs are slug-derived from names, optionally namespaced under a parent:

```ts
const normalized = name
  .toLowerCase()
  .replace(/[_\s]+/g, "-")
  .replace(/[^a-z0-9-]/g, "")
  .replace(/-+/g, "-")
  .replace(/^-|-$/g, "");
return parentId ? `${parentId}/${normalized}` : normalized;
```

This is human-readable URL-style ID (`auth-module/login-flow`), not UUIDs. Pleasant for agents to reason about, but means renames cascade.

---

## 2. Engram's analogue

### Engram relation types

From `lib/engram_graph_walker.py:44-65` and `lib/engram_wave2_schema.py`:

```sql
CREATE TABLE IF NOT EXISTS memory_relations (
  id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  relation TEXT NOT NULL DEFAULT 'pending',
  ...
  superseded_at TEXT,
  superseded_by_relation_id INTEGER,
  judgment_status TEXT,           -- 'pending' / 'approved' / 'rejected'
);
```

The relation vocabulary observed in code and CLAUDE.md's CONFLICT SURFACING protocol:

```
supersedes        ← temporal validity, drives `valid_to`
conflicts_with    ← divergent claims requiring judgment
related           ← weak associative
compatible        ← compatible co-existing claims
scoped            ← narrower-scope variant
not_conflict      ← explicit non-conflict assertion
pending           ← default until mem_judge resolves
```

Plus `judgment_status` lifecycle (`pending` / `approved` / `rejected`), which MegaMemory has no analogue for.

### Engram concept-kind analogue

Engram uses free-form `type` strings (`bugfix`, `decision`, `architecture`, `discovery`, `pattern`, `config`, `preference`) plus a planned MIRIX-style `memory_class` overlay (semantic / episodic / procedural / working, per `docs/reports/cross-check-A-memory-2026-05-08.md` §🔍12).

---

## 3. Verdict per dimension

| Dimension | MegaMemory | Engram | Verdict |
|---|---|---|---|
| Node-kind expressiveness | 6 fixed enum kinds | Free-form `type` + planned MIRIX memory_class | **IGUAL** for coverage today; **MEJOR_NUESTRO** planned. MegaMemory's fixed enum is friendlier for static validation but inflexible. |
| Relation vocabulary | 5 directed connects/depends/impl/calls/configures | 6+ governance-aware relations including temporal/judgment semantics | **MEJOR_NUESTRO** |
| Temporal model | `created_at` / `updated_at` / `removed_at` only | `superseded_at` + `valid_to` planned (Graphiti port) | **MEJOR_NUESTRO** |
| Soft delete | Tombstone + reason (`removed_at`, `removed_reason`) | Same shape via Engram observation lifecycle | **IGUAL** |
| Multi-process safety | WAL + busy_timeout=5000 + `BEGIN IMMEDIATE` migrations | Engram daemon serializes writes | **IGUAL** (different shape, both safe) |
| Edge dedup | UNIQUE(from,to,relation) (schema v4) | `judgment_status` + relation lifecycle | **IGUAL** |
| Hierarchical parent_id | Self-FK, ON DELETE SET NULL | Implicit via `topic_key` namespacing | MegaMemory more explicit; **IGUAL** in practice. |
| ID readability | Slug paths (`auth/login-flow`) | UUID-like sync_ids + human topic_key | **NO_COMPARABLE** (style preference) |
| Embedding column | `embedding BLOB` directly on `nodes` | FTS5 today; no embedding column yet | **MEJOR_EXTERNO** narrowly (their embedded model fits a single column; we will add this when LightRAG slice lands) |

**Net for Annex A:** MegaMemory's schema is clean, well-migrated, and competently locked. But the relation model is **too thin for COS governance** — no judgment, no supersession, no conflict-typing — and that gap is precisely where Engram earns its keep. The one pattern worth borrowing here is the **single-column `embedding BLOB` next to the typed row** (vs a sidecar table); that's already implicit in the LightRAG port plan, but it's nice to see it confirmed in working production code.

---

## 4. Port-relevant snippets

- The pragma block and migration chain (`src/db.ts:20-178`) is a tidy reference for any future Engram embedding-column migration.
- The dedup-then-unique-index pattern in schema v4 (`src/db.ts:158-169`) is exactly how we would clean up any legacy duplicate `memory_relations` rows before adding stricter constraints.
- The ID-slug routine (`src/tools.ts:33-41`) is **not** worth porting — Engram's topic_key is already richer.

No code is vendored. References only.
