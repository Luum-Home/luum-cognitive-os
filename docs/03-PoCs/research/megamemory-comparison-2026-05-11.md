---
title: "MegaMemory Deep Comparison — luum-agent-os vs MegaMemory"
date: 2026-05-11
author: orchestrator
status: draft
source-repo: ".cognitive-os/external-source-cache/MegaMemory (v1.6.2, commit e0bb3c2, 2026-05-02)"
scope: research-only
license_constraint: "MIT — adoption legally clean, but pattern extraction preferred for runtime independence (single-author project, <10k node ceiling, redundant runtime vs Engram)"
related_docs:
  - docs/03-PoCs/research/repo-scout/deep/0xK3vin__MegaMemory-2026-05-11.md
  - docs/06-Daily/reports/external-tools-radar-megamemory-addendum-2026-05-11.md
  - docs/03-PoCs/research/holaos-comparison-2026-05-10.md
  - docs/04-Concepts/architecture/memory-layer-evolution-sdd.md
  - docs/06-Daily/reports/cross-check-A-memory-2026-05-08.md
---

# MegaMemory Deep Comparison — luum-agent-os vs MegaMemory

> Phase-3 axis verdicts: OURS_BETTER / EQUIVALENT / EXTERNAL_BETTER / NOT_COMPARABLE.
> Research-only artifact, parallel to the holaOS comparison shape. Adoption decision
> is already taken (ASSESS / pattern-only) in `docs/06-Daily/reports/external-tools-radar-megamemory-addendum-2026-05-11.md`;
> this corpus drills the why behind that verdict and pins port surfaces.

---

## 1. Resumen ejecutivo

MegaMemory (0xK3vin, 2026) is a single-binary **MCP server** that gives coding agents a persistent project-scoped **concept knowledge graph**. The shape is striking in its minimalism:

- **TypeScript** (Node ≥18), ~5k LOC across 12 source files (`src/*.ts`), MIT.
- **libsql/SQLite** with WAL, schema v4, soft-delete, append-only `timeline` audit table.
- **In-process embeddings**: `@xenova/transformers` running `Xenova/all-MiniLM-L6-v2` (384-dim, quantized ONNX, ~23MB auto-download, **no API key**).
- 9 MCP tools: `understand`, `get_concept`, `create_concept`, `update_concept`, `link`, `remove_concept`, `list_roots`, `list_conflicts`, `resolve_conflict`.
- A **two-way merge engine** with explicit conflict surfacing tools (`list_conflicts` + `resolve_conflict`).
- A **D3-force / HTML canvas** web explorer (`megamemory serve`).
- A **multi-editor installer** for opencode / claudecode / antigravity / codex.

License is clean MIT — direct vendoring is legally allowed. But the runtime is functionally redundant with Engram and weaker on every governance dimension (typed relations, bi-temporal plan, memory_class plan, capacity, bus factor). The **single extractable primitive** worth porting now is the in-process MiniLM embedding pipeline; everything else is at best a reference design.

**Verdict (already taken):** ASSESS / pattern-only (algorithm port). Fold the in-process-embedding pattern into the planned LightRAG dual-level slice. Do not adopt the runtime, do not vendor, do not register a parallel MCP memory server.

---

## 2. License posture and adoption stance

- **License**: MIT. `LICENSE` file inspected in the clone.
- **Per `rules/license-policy.md`**: ALLOW (no AGPL/SSPL/BUSL drag, no branding clauses).
- **Adoption kind** (`docs/04-Concepts/architecture/external-tool-adapter-taxonomy.md`): **algorithm port** — pattern-only.
- **Why not runtime adoption** despite a permissive license:
  - Single-author project, stated <10k node ceiling, no bi-temporal model.
  - Engram already covers concept-graph shape with richer typed relations (`supersedes`, `conflicts_with`, `related`, `compatible`, `scoped`, `not_conflict`).
  - A second SQLite-backed memory plane next to Engram would duplicate the persistence layer without adding an algorithm we don't already plan to acquire from LightRAG/HippoRAG/MIRIX.
- **What MIT enables that BSL-like licenses (e.g., holaOS) would not**: we can directly vendor short, well-bounded files such as `src/embeddings.ts` with attribution if the Python port ever proves cheaper to mirror than to rewrite. Default stance remains: **rewrite, attribute, don't vendor**, because the dependency footprint (`@xenova/transformers` → `onnxruntime-node`) does not map to our Python stack.

---

## 3. Repository map (from the clone)

| Path | LoC | Role |
|---|---:|---|
| `src/types.ts` | 221 | Data model: `NodeKind` (6 kinds), `RelationType` (5 kinds), DB row types, merge/conflict types. |
| `src/db.ts` | 917 | `KnowledgeDB` — libsql open, WAL, busy_timeout, schema v1→v4 migrations, transaction helpers, all CRUD. |
| `src/embeddings.ts` | 122 | Lazy-loaded `@xenova/transformers` MiniLM extractor, `embed`, `cosineSimilarity`, `findTopK`. |
| `src/tools.ts` | 410 | MCP tool handlers: `understand`, `getConcept`, `createConcept`, `updateConcept`, `link`, `removeConcept`, `listRoots`, `listConflicts`, `resolveConflict`. |
| `src/index.ts` | 542 | CLI router + MCP stdio server registration of all 9 tools with `timeline.log` instrumentation. |
| `src/install.ts` | 724 | Multi-editor installer (opencode/claudecode/antigravity/codex), JSONC parser, managed-file marker. |
| `src/merge.ts` | 551 | `MergeEngine` — two-DB read-only merge into fresh output, conflict detection, `merge_group` UUID assignment. |
| `src/merge-cli.ts` | 296 | `megamemory merge` / `conflicts` / `resolve` CLI surface. |
| `src/web.ts` | 791 | HTTP server for graph explorer (`/api/*` endpoints + static `web/index.html`). |
| `src/timeline.ts` | 36 | Append-only audit logger writing every tool invocation to the `timeline` table. |
| `src/stats.ts` | 170 | `megamemory stats` CLI — node/edge/embedding counts. |
| `src/cli-utils.ts` | 203 | Picocolors-styled CLI helpers, port validation, `multiSelect`. |
| `web/index.html` | (single file) | D3 v7.9.0 (CDN) + Canvas 2D force-directed explorer. |
| `plugin/megamemory.ts` | — | OpenCode plugin entrypoint registered as `megamemory` tool. |
| `commands/` | — | Slash-command source files for `/bootstrap-memory` and `/merge`. |

The whole thing fits in one head. That is partly its appeal and partly its limit.

---

## 4. Comparison framing

MegaMemory is compared along two axes:

1. **vs Engram** (our in-house persistent memory) — the closest one-for-one peer.
2. **vs the planned memory bundle** (Graphiti / LightRAG / HippoRAG / MIRIX, per `docs/04-Concepts/architecture/memory-layer-evolution-sdd.md`) — the family that MegaMemory is implicitly competing with for the same slot.

A condensed verdict matrix:

| Dimension | MegaMemory | Engram + planned bundle | Verdict |
|---|---|---|---|
| Storage substrate | SQLite WAL + soft-delete + timeline | Engram daemon over SQLite + `memory_relations` | EQUIVALENT |
| Embedding source | In-process MiniLM 384-dim ONNX | FTS5-only today; LightRAG slice planned | EXTERNAL_BETTER (narrow primitive) |
| Relation typing | 5 directed relations (`connects_to`, `depends_on`, `implements`, `calls`, `configured_by`) | 6+ judgment-aware relations (`supersedes`, `conflicts_with`, `related`, `compatible`, `scoped`, `not_conflict`) with `judgment_status` lifecycle | OURS_BETTER |
| Concept-kind taxonomy | 6 fixed kinds | Free-form `type` strings + planned MIRIX memory_class | EQUIVALENT on coverage; MIRIX path more expressive |
| Conflict surfacing | Explicit `list_conflicts` + `resolve_conflict` MCP tools | `judgment_required` envelope + per-candidate `mem_judge` (CLAUDE.md "CONFLICT SURFACING") | EQUIVALENT (different ergonomics, same outcome) |
| Bi-temporal model | None | Planned via Graphiti adoption (`valid_to` via `memory_relations.superseded_at`) | OURS_BETTER |
| Graph walk | Cosine over candidates + 1-hop lookup | BFS with typed-edge filtering (`lib/engram_graph_walker.py`) + planned HippoRAG PPR | OURS_BETTER |
| Explorer UI | D3-force web view (`megamemory serve`) | None | EXTERNAL_BETTER (not a current requirement) |
| Audit trail | Append-only `timeline` table per tool invocation | Engram observations + judgment lifecycle + sessions | EQUIVALENT (different shape, same coverage) |
| Capacity ceiling | <~10k nodes (stated) | Unbounded via FTS5 + Engram daemon | OURS_BETTER |
| Harness portability | Per-target installer (4 harnesses) | `.ai/` portable overlay (ADR-258) + manifest-driven adoption | OURS_BETTER |
| Dependency footprint | `@xenova/transformers`, `libsql`, `zod`, `picocolors`, MCP SDK | Stdlib-heavy Python + Engram daemon; embedder TBD | MegaMemory heavier on a port |
| Bus factor | Single author | Multi-author project core | OURS_BETTER |

**Net:** MegaMemory wins narrowly on **two** dimensions (in-process embedder, explorer UI) and loses on everything else. The win is real but is a single primitive's worth, not a system's worth.

---

## 5. Annexes

| Annex | Topic |
|---|---|
| [A — Concept graph & relation model](./megamemory-annex-a-concept-graph-2026-05-11.md) | The 6 kinds × 5 relations schema, SQLite v4 migration chain, comparison vs Engram's typed-relation graph. |
| [B — In-process embeddings (port target)](./megamemory-annex-b-embeddings-port-2026-05-11.md) | `@xenova/transformers` pipeline, cosine-search loop, Python port plan via `sentence-transformers`. **The canonical primitive to extract.** |
| [C — MCP tool surface & conflict-merge](./megamemory-annex-c-mcp-merge-2026-05-11.md) | All 9 MCP tool signatures, merge engine, `list_conflicts` / `resolve_conflict` vs `judgment_required` / `mem_judge`. |
| [D — Explorer UX & installer](./megamemory-annex-d-explorer-installer-2026-05-11.md) | D3-force/Canvas explorer, multi-editor installer (opencode/claudecode/antigravity/codex), comparison vs ADR-258 portable overlay. |
| [E — Extractable primitives](./megamemory-annex-e-primitives-2026-05-11.md) | Ranked port list with cost, complexity, vendor-vs-port decisions, alignment with memory-bundle SDD. |

---

## 6. One-line verdict

MIT-licensed and competently built, but Engram-redundant at runtime and single-author below COS bus-factor floor. **Port the in-process MiniLM pipeline (Annex B), nothing else.**
