---
report_type: external-tools-radar-addendum
subject: 0xK3vin/MegaMemory
generated_at: 2026-05-11
status: assess-pattern-only
related_adrs: [ADR-065, ADR-247, ADR-254]
source_artifacts:
  - docs/03-PoCs/research/repo-scout/deep/0xK3vin__MegaMemory-2026-05-11.md
related_docs:
  - docs/06-Daily/reports/cross-check-A-memory-2026-05-08.md
  - docs/04-Concepts/architecture/external-tool-adoption-doctrine.md
  - docs/04-Concepts/architecture/external-tool-adapter-taxonomy.md
  - docs/04-Concepts/architecture/memory-layer-evolution-sdd.md
  - docs/04-Concepts/patterns/ecosystem-tools.md
---

> **License attribution.** Code excerpts and structural descriptions quoted from `0xK3vin/MegaMemory` v1.6.2 (MIT License, Copyright (c) 2026 0xk3vin — see https://github.com/0xK3vin/MegaMemory/blob/main/LICENSE). MIT permits direct vendoring with copyright preservation. See [`megamemory-annex-f-compliance-cleanroom-2026-05-11.md`](../research/megamemory-annex-f-compliance-cleanroom-2026-05-11.md) for the full compliance protocol and port-vs-vendor decisions.

# External Tools Radar — MegaMemory Addendum (2026-05-11)

## Decision

Add [0xK3vin/MegaMemory](https://github.com/0xK3vin/MegaMemory) to the radar as **ASSESS / pattern-only**.

MegaMemory is a TypeScript MCP server providing a persistent project-scoped concept knowledge graph with in-process MiniLM embeddings, SQLite storage, a D3-force web explorer, and a two-way merge engine with conflict resolution. It is a credible, MIT-licensed peer to Engram in shape, but it is **functionally redundant with Engram at the runtime level** and weaker in governance semantics. The extractable value is one specific pattern: **in-process embeddings without an API key**, which fits cleanly into the already-planned LightRAG dual-level port.

## Bidirectional comparison vs Engram and the memory bundle

Verdicts use the Phase 3 axis (OURS\_BETTER / EQUIVALENT / EXTERNAL\_BETTER / NOT\_COMPARABLE) and cite concrete COS files.

### vs Engram (in-house persistent memory)

| Dimension | MegaMemory | Engram (COS) | Verdict |
|---|---|---|---|
| Storage substrate | SQLite + WAL + schema v3 | SQLite via daemon (`lib/engram_client.py`, `lib/engram_http_client.py`) | **EQUIVALENT** |
| Embeddings | In-process MiniLM, no keys | FTS5 baseline + optional Cognee HTTP (`lib/cognee_client.py`); no in-process embedder | **EXTERNAL_BETTER** (narrow: just the in-process pipeline) |
| Relation typing | Single `link` verb | Typed relations: supersedes / conflicts\_with / related / compatible / scoped (`lib/engram_graph_walker.py`) | **OURS_BETTER** |
| Conflict surfacing | `list_conflicts` + `resolve_conflict` MCP tools | `judgment_required` envelope + per-candidate `mem_judge` (CLAUDE.md "CONFLICT SURFACING") | **EQUIVALENT** (we cover it; their public verb shape is a nicer portability cue) |
| Bi-temporal | None | Planned via graphiti adoption (`docs/06-Daily/reports/cross-check-A-memory-2026-05-08.md` §graphiti); `memory_relations` already has `created_at` / `superseded_at` | **OURS_BETTER** (current and planned) |
| Memory class taxonomy | Concepts only | MIRIX-style `memory_class` overlay planned (`cross-check-A` §🔍12); current type strings cover bugfix/decision/architecture/discovery/pattern/config/preference | **OURS_BETTER** |
| Graph walk | Cosine + lookup | BFS with typed relations + planned PPR (HippoRAG port, `cross-check-A` §HippoRAG) | **OURS_BETTER** |
| Explorer UI | D3-force web view | None | **EXTERNAL_BETTER** (pattern only — not a current COS requirement) |
| Capacity | <~10k nodes (stated) | Unbounded in practice via FTS5 | **OURS_BETTER** |
| Harness portability | Per-target installer (opencode/claudecode/antigravity/codex) | `.ai/` portable overlay (ADR-258) + `manifests/external-tools-adoption.yaml` | **OURS_BETTER** |
| Bus factor | Single author | Project core, multi-author | **OURS_BETTER** |

**Net vs Engram:** **EQUIVALENT** in concept-graph shape; **EXTERNAL_BETTER** narrowly on in-process embeddings + explorer; **OURS_BETTER** on every governance dimension. Runtime adoption would be a regression.

### vs the memory bundle (Graphiti / LightRAG / HippoRAG / MIRIX)

Reference: `docs/04-Concepts/architecture/memory-layer-evolution-sdd.md`, `docs/06-Daily/reports/cross-check-A-memory-2026-05-08.md`.

| Bundle component | Provides | MegaMemory overlap | Verdict |
|---|---|---|---|
| **Graphiti** | Bi-temporal edges (`valid_from`/`valid_to` + `ingested_at`), cross-encoder rerank | None | Bundle wins; MegaMemory **NOT_COMPARABLE** on temporality. |
| **LightRAG** | Dual-level (entity + topic) retrieval scoring fusion | Single-level cosine on concept embeddings | Bundle wins on algorithm; MegaMemory contributes the **in-process embedding** delivery vehicle that LightRAG's algorithm needs in-house. **Complementary**. |
| **HippoRAG** | Personalized PageRank over entity graph | None (no multi-hop scoring) | Bundle wins; **NOT_COMPARABLE**. |
| **MIRIX** | Semantic / episodic / procedural / working memory_class taxonomy | None (concepts are flat) | Bundle wins; **NOT_COMPARABLE**. |

**Net vs bundle:** the memory bundle dominates on algorithms (bi-temporal, dual-level, PPR, taxonomy). MegaMemory contributes exactly one orthogonal slice — **in-process embeddings with no API key dependency** — which is a useful delivery primitive *under* the LightRAG dual-level algorithm rather than a replacement for any bundle component.

## Adoption kind (per `external-tool-adapter-taxonomy.md`)

**Algorithm port (pattern-only).** Extract the in-process MiniLM embedding pipeline; rewrite in Python using `sentence-transformers` MiniLM (or equivalent) inside `lib/engram_lifecycle.py` as the embedding source for the planned LightRAG dual-level retrieval port. Do **not**:

- vendor the TypeScript runtime,
- expose a parallel MCP memory server,
- adopt the multi-editor installer (we have ADR-258 `.ai/` overlay),
- import the concept-graph schema (we have richer typed relations).

Optionally borrow the public MCP tool *names* (`list_conflicts`, `resolve_conflict`) as portability aliases over `mem_judge` — pure surface ergonomics, no semantic change.

## Recommendation

**ASSESS / pattern-only.** Track in `docs/04-Concepts/patterns/ecosystem-tools.md` under EVALUATE. Fold the in-process-embedding pattern into the existing memory-bundle work; do not open a separate adapter lab.

### Acceptance criteria (if pattern is ever ported)

1. In-process embedding source plugged into `lib/engram_lifecycle.search()` behind a feature flag, with cold-start <2s on the project Engram corpus.
2. Embedding model artifact tracked under `manifests/external-tools-adoption.yaml` with license + provenance (expected Apache-2.0 for MiniLM, must be verified at port time).
3. Dual-level (entity + topic) scoring delta measurable on the existing Engram corpus: ≥10% improvement on semantic-recall A/B vs FTS5-only baseline, or the port is reverted.
4. No new MCP server registered. No new SQLite store. Engram remains the single memory plane.
5. `judgment_required` / `mem_judge` semantics unchanged; if MegaMemory's tool names are aliased, they MUST route to the existing judgment flow.

### Rollback path

- The pattern lives behind a single feature flag in `lib/engram_lifecycle.py`. Disable flag → revert to FTS5 (+ optional Cognee) baseline.
- The embedding model is a single on-disk artifact; remove the file + flag to fully detach.
- No upstream MegaMemory code is vendored, so there is no fork-maintenance debt to clean up.

## Why ASSESS, not ADOPT

- Runtime is functionally redundant with Engram and weaker in governance (typed relations, bi-temporal plan, memory_class plan, capacity).
- Single-author project, <10k-node stated ceiling, no bi-temporal / no PPR / no taxonomy.
- The only valuable delta (in-process embeddings) is a ~3-5 day Python port that doesn't require depending on MegaMemory at all.

## Why not REJECT

- License is clean MIT.
- The pattern is genuinely useful and aligns with already-planned work.
- No security or supply-chain red flags; no AGPL/SSPL/BUSL drag.
- The repo is worth re-checking if (a) the user-facing graph explorer becomes a requirement, or (b) we ever need a second harness-portable memory MCP independent of Engram.

## Follow-up trigger

Open a port spike only when the memory-bundle SDD (`docs/04-Concepts/architecture/memory-layer-evolution-sdd.md`) reaches the LightRAG dual-level slice and we need an in-process embedder choice. At that point, fold the MegaMemory pattern into that slice's design doc — do not create a parallel MegaMemory adapter lab.
