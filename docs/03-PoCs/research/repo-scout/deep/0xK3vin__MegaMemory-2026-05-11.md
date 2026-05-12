---
report_type: repo-scout-deep
subject: 0xK3vin/MegaMemory
generated_at: 2026-05-11
classification: ASSESS
verdict_vs_engram: IGUAL (en concept-graph local) / MEJOR_EXTERNO (en explorer UI + in-process embeddings) / MEJOR_NUESTRO (en governance + bi-temporal + memory_class)
related_adrs: [ADR-065, ADR-247, ADR-254]
source_url: https://github.com/0xK3vin/MegaMemory
license: MIT
---

# Deep Evaluation — 0xK3vin/MegaMemory (2026-05-11)

## 1. Identity

| Field | Value |
|---|---|
| Owner / Repo | `0xK3vin/MegaMemory` |
| One-liner (≤120ch) | MCP server: persistent concept-graph for coding agents with in-process embeddings, SQLite store, and D3 web explorer. |
| License | MIT (permissive — allowed per `rules/license-policy.md`) |
| Stars | ~156 (unverified upstream — only WebFetch sample) |
| Last commit | 2026-05-02, `e0bb3c2` "chore: bump version to 1.6.2" (verified from shallow clone on 2026-05-11) |
| Primary language | TypeScript (~70%) |
| CI | Not directly inspected; CHANGELOG shows 9+ tagged releases — release cadence suggests automated tagging (unverified upstream) |
| Maturity | Early-to-mid stage; single-author personal project; active. |

## 2. One-liner

MegaMemory is a stdio MCP server that gives coding agents a persistent, project-scoped **concept knowledge graph** with semantic search (in-process MiniLM embeddings, no API keys), a D3-force web explorer, and a two-way merge engine with conflict surfacing.

## 3. Technical architecture

- **Storage:** SQLite (WAL mode), schema v3, soft-delete history.
- **Memory primitive:** "Concept" nodes + typed links (no symbol/file granularity; this is **semantic**, not code-AST). Roughly analogous to Engram observations + `memory_relations`.
- **Embeddings:** In-process via `@xenova/transformers` (`all-MiniLM-L6-v2`, 384-dim). No external embedding API. Capacity bounded (<~10k nodes per docs).
- **Retrieval:** Cosine similarity on node embeddings + concept lookup; no dual-level (entity+topic) fusion, no PPR.
- **Tools (9 MCP):** `understand`, `get_concept`, `create_concept`, `update_concept`, `link`, `remove_concept`, `list_roots`, `list_conflicts`, `resolve_conflict`.
- **Conflict model:** Two-way merge, conflicts surfaced by concept ID, explicit `resolve_conflict` tool. This is comparable to Engram's `judgment_required` envelope but operates on concept content rather than typed relations (supersedes/conflicts_with).
- **UX:** D3-force graph explorer served by `megamemory serve`.
- **Installer:** Multi-editor (`opencode`, `claudecode`, `antigravity`, `codex`) — writes per-harness MCP wiring.

## 4. Weighted score (repo-scout rubric)

| Dimension | Weight | Score (0-5) | Notes |
|---|---:|---:|---|
| Primitive value (extractable patterns) | 0.30 | 3 | Concept-graph + in-process embeddings + conflict-resolve loop are clean ideas. |
| License posture | 0.15 | 5 | MIT, no patent clauses, no NOTICE drag. |
| Maturity / activity | 0.15 | 3 | Active (May 2026), 15 releases, but single author and ~156 stars. |
| Architectural fit with Engram | 0.15 | 3 | Same primitive shape (graph + search + merge) but TS+SQLite vs our Python+SQLite+FTS5; conceptual overlap is high but runtime overlap is duplicative. |
| Integration cost | 0.10 | 2 | Adopting the runtime = second MCP memory server competing with Engram. Adopting patterns only = cheap. |
| Risk surface | 0.10 | 3 | In-process embeddings (no key leak), local SQLite, MCP-only — low. Single-author bus factor and bounded capacity are the real risks. |
| Governance alignment | 0.05 | 2 | No bi-temporal, no MIRIX-style memory_class, no relation taxonomy beyond `link`. |

**Weighted total:** ~3.05 / 5 → **ASSESS** tier (pattern-extract; do not adopt runtime).

## 5. Classification

**ASSESS** (with **pattern-only** adoption posture per `docs/04-Concepts/architecture/external-tool-adapter-taxonomy.md`).

Rationale: MegaMemory is a credible, well-scoped concept-graph MCP, but it is **functionally redundant with Engram** at the runtime level (both are local SQLite-backed agent memory MCP servers). What it does *better* (in-process embeddings, explorer UI, explicit conflict-resolve tool surface) is extractable as patterns. What it does *worse* relative to Engram (no typed relations beyond `link`, no bi-temporal, no memory_class, no project-overlay model, ~10k node cap, single author) makes runtime adoption a regression.

## 6. Primitive extraction candidates vs Engram

| Candidate primitive | Source in MegaMemory | COS analogue | Verdict | Effort |
|---|---|---|---|---|
| **In-process embedding pipeline** (Xenova MiniLM, no API keys) | `understand` + create/update flow | Engram lacks in-process embeddings; relies on FTS5 + optional Cognee. See `lib/engram_http_client.py`, `lib/engram_lifecycle.py`. | MEJOR_EXTERNO — adopt-pattern (algorithm port). Combine with the **LightRAG dual-level** plan from `docs/06-Daily/reports/cross-check-A-memory-2026-05-08.md` §🔍2: in-process embedding fills the same gap as Cognee opt-in. | 3-5 days port (Python equivalent via `sentence-transformers` MiniLM); cost: one ~80MB model on disk. |
| **Explicit `resolve_conflict` MCP tool surface** | 9-tool list | Engram surfaces conflicts via `judgment_required` envelope + `mem_judge` (CLAUDE.md "CONFLICT SURFACING"). Functionally equivalent but ours is per-candidate. | IGUAL — already covered by `mem_judge`. Worth borrowing the *tool name and verb shape* for the public MCP surface for harness portability. | 0.5 day (rename/alias). |
| **D3-force graph explorer** | `megamemory serve` | No equivalent in COS. Engram has CLI inspectors, no graph UI. | MEJOR_EXTERNO — pattern-only (study UX, do not vendor JS bundle). | Out of scope; deferred to a future "Engram explorer" tracker item. |
| **Two-way merge engine with concept-ID conflicts** | Merge code path | Engram has typed relations (supersedes/conflicts_with/related/compatible/scoped) which is richer; MegaMemory's binary "concept conflict" is a subset. | MEJOR_NUESTRO. | None. |
| **Multi-editor installer** (opencode/claudecode/antigravity/codex) | `megamemory install --target` | `manifests/external-tools-adoption.yaml` + `.ai/` overlay (ADR-258) cover this with broader scope. | IGUAL / MEJOR_NUESTRO — our portable overlay generalizes. | None. |
| **Concept-graph primitive itself** | Schema v3 | Engram `memory_relations` already implements this with richer typing + soft-delete + topic_key + bi-temporal candidates from graphiti cross-check. | IGUAL in shape, MEJOR_NUESTRO in semantics. | None. |
| **<10k node capacity ceiling** | Doc-stated limit | Engram is FTS5-backed and unbounded in practice. | MEJOR_NUESTRO. | None. |

**Net extraction recommendation:** port the in-process embedding pipeline (combined with the already-recommended LightRAG dual-level plan), borrow the public MCP tool naming as a portability gesture, study the explorer UX. Do **not** vendor the runtime.

## 7. Integration cost estimate

- **Pattern-only path (recommended):** 3-5 days for in-process embeddings into `lib/engram_lifecycle.py` ranking; 0.5 day MCP-tool alias study. No new dependency on the MegaMemory project.
- **Adapter path (not recommended):** would duplicate Engram with a parallel TS MCP server, fragmenting the memory plane. Cost is not just integration days — it is governance cost (two stores, two conflict models, two backup paths).

## 8. Risks

1. **Bus factor:** single-author repo. Pattern extraction is fine, runtime dependency is not.
2. **Node-count ceiling:** <10k concepts is below the steady-state Engram observation volume in this project; the runtime would not scale.
3. **Semantic-only granularity:** MegaMemory has no episodic/procedural/working classes (MIRIX gap re-introduced if we adopted it as the canonical store).
4. **No bi-temporal:** would regress on the graphiti adoption already planned (`cross-check-A-memory-2026-05-08.md` §🔍2 graphiti).
5. **MCP-stdio coupling:** the installer writes harness-specific config; would compete with `.ai/` portable overlay (ADR-258).
6. **Embeddings model footprint:** ~80MB on-disk MiniLM. Acceptable for pattern port; would need license + provenance review on the model card (Apache-2.0 expected, unverified upstream).

## 9. Verification status (updated 2026-05-11)

Initial assessment used a single WebFetch; verified on 2026-05-11 against a shallow clone of `0xK3vin/MegaMemory`. Authoritative findings from the clone:

- **License:** MIT (LICENSE file head: "MIT License / Copyright (c) 2026 0xk3vin") — verified.
- **Version:** `package.json` reports `1.6.2`; latest commit `e0bb3c2 chore: bump version to 1.6.2` dated 2026-05-02 — verified.
- **Tool surface:** 9 MCP tools listed in README — verified (`understand`, `get_concept`, `create_concept`, `update_concept`, `link`, `remove_concept`, `list_roots`, `list_conflicts`, `resolve_conflict`).
- **Concept kinds + relation types:** 6 kinds + 5 relation types verified verbatim in README and CHANGELOG.
- **Scale ceiling:** README line 195 states cosine-similarity search "fast enough for graphs with <10k nodes" — verified verbatim.
- **Embedding model:** `all-MiniLM-L6-v2`, 384-dim, in-process via `@xenova/transformers` — verified in README.

Still unverified upstream (low-impact on ASSESS decision):

- Exact star count (~156 was a single WebFetch sample, not authoritative).
- CI workflow contents (not inspected; release cadence in CHANGELOG suggests tagged automation).
- Embedding-model license card (Apache-2.0 expected, must be re-verified at port time).

## 10. Decision

**ASSESS — pattern-only.** Do not adopt the runtime. Harvest the in-process-embedding pattern as part of the LightRAG dual-level port already planned in the 2026-05-08 memory cross-check. Re-evaluate only if: (a) we ever need a second harness-portable memory MCP independent of Engram, or (b) the explorer UX becomes a user-facing requirement and porting one is cheaper than building one.
