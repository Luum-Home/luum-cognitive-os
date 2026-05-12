---
title: "HelixDB Annex E — Ranked extractable primitives"
date: 2026-05-11
parent: helixdb-comparison-2026-05-11.md
scope: research-only
license_constraint: "AGPL-3.0 — pattern-only adoption, clean-room rewrite required. Every primitive below MUST be implemented from first principles, NOT by translating helix source. ADR-required before any implementation begins."
engram_topic_key: tech-radar/helix-db/primitives
verdict_runtime: REJECT
verdict_pattern: TRIAL-PATTERNS
verdict_pattern_history:
  - 2026-05-11 initial: HOLD / pattern-only
  - 2026-05-11 reconciled: TRIAL-PATTERNS (cluster-B coherence audit; top 3 primitives below, clean-room 3-5 PW combined; iFixAi Phase 12 precedent)
---

# Annex E — Ranked extractable primitives

## §1 — Verdict

- **Runtime / dependency**: REJECT (AGPL-3.0 BLOCK — see parent §4 and addendum).
- **Pattern lane**: TRIAL-PATTERNS. Promoted from HOLD on 2026-05-11 after cluster-B coherence audit: the top 3 primitives below (E.1 typed-ADT MCP surface, E.2 reranker fusion, E.3 hoisted-embedding / IO-continuation) total 3-5 PW clean-room cost — consistent with TRIAL-PATTERNS doctrine in `docs/architecture/external-tool-adapter-taxonomy.md`. Precedent: iFixAi (Phase 12) — same shape, TRIAL-PATTERNS posture. Primitives §E.4-E.9 remain HOLD/conditional/anti-recommended as already noted.

Ranking criterion: **extraction value = alignment with COS roadmap × novelty over already-shipped Engram × clean-room cost⁻¹**.

| # | Primitive | Value | Roadmap fit | Clean-room cost |
|---|---|---|---|---|
| 1 | Typed-ADT MCP tool surface (recursive enum + serde discriminator) | HIGH | Direct — Engram MCP tools are flat verbs today | LOW (1–2 PW) |
| 2 | Reranker fusion layer (RRF + MMR + score-normalizer split) | HIGH | Direct — needed for LightRAG dual-level + any hybrid search | LOW (1 PW) |
| 3 | Hoisted-embedding / IO-continuation pattern | MEDIUM-HIGH | Direct — applicable to Engram crystallizer pipeline | LOW (1–2 PW) |
| 4 | Compiled-DSL contract (parse → analyze → codegen Rust) | MEDIUM | Conditional — only if Engram grows a typed agent-facing API | HIGH (6–10 PW) |
| 5 | Filter-aware HNSW (filter during level-walk, not post-filter) | MEDIUM | Conditional — only if we build a custom vector index | MEDIUM (3–4 PW) |
| 6 | Two-way inverted index (forward + reverse postings) | LOW-MEDIUM | Conditional — only if we replace FTS5 | LOW (2 PW) |
| 7 | Single-writer / N-reader worker pool with flume-bounded channels | LOW | Far horizon — no COS subsystem needs it today | LOW (1 PW) |
| 8 | LMDB-everything substrate (graph + vector + FTS + meta in one Env) | NEGATIVE | Anti-fit — SQLite is the right answer at our scale | HIGH (4–6 PW + ops cost) |
| 9 | Compile-time route inventory pattern (`inventory::submit!`) | LOW | Not applicable — Python orchestrator does not link a Rust binary | n/a |

The top three are the only ones I would advocate adopting under the current COS roadmap. The rest are documented for completeness.

---

## E.1 — Typed-ADT MCP tool surface

### Pattern

The MCP tool catalogue is a **closed, recursive algebraic data type** of traversal/operation primitives parameterized by literal labels and value-typed arguments. The agent does not send strings; it sends a structured composition of typed steps. The server-side schema (here: serde + a Rust enum with `#[serde(tag, content)]`) is the *grammar*. Invalid compositions cannot be expressed.

### Why this matters for COS

Engram MCP today exposes flat verbs (`mem_save`, `mem_search`, `mem_get_observation`, …). Each is a leaf. There is no notion of "filter results of mem_search by predicate then crystallize". If/when Engram grows a query-style surface (e.g. for `/recall-search` to express richer queries than a single search string), the typed-ADT pattern gives us:

- A grammar that is part of the schema, validated at deserialisation time.
- An MCP tool surface that LLM agents can be schema-prompted on (clients introspect the enum variants).
- A direct mapping from tool variants to Engram primitives — no string parsing.

### Clean-room reimplementation contract

1. **Variant names must be COS verbs**, not graph-traversal verbs. Suggested set: `Recall { topic_key, scope }`, `RelatedTo { observation_id, depth }`, `Filter { predicate }`, `Crystallize { observation_ids }`, `Hybrid { fts_query, vector_query, fuser }`. Do not use `OutStep`, `InStep`, `NFromType`, etc.
2. **Do not copy the serde tag format** (`tag = "tool_name", content = "args"`). Choose `kind`/`payload` or similar.
3. Re-derive recursion from the requirement ("compose Engram operations") not from `FilterTraversal`'s structure.
4. The implementation lives under `lib/engram_*.py` or a new module; cross-reference this annex in the ADR but not the helix source.

### Effort

1–2 PW including serde-equivalent (pydantic) wiring and MCP tool publication.

---

## E.2 — Reranker fusion layer (RRF + MMR + score-normalizer)

### Pattern

Hybrid retrieval is **not** an SQL union of vector + FTS results. It is an explicit reranker layer with at minimum:

- **RRF** (Reciprocal Rank Fusion): calibration-free combiner; default `k = 60`. Operates only on ranks, not scores. Correct default for BM25 ⊕ vector hybrid because the score distributions are non-commensurable.
- **MMR** (Maximal Marginal Relevance): diversity-aware re-selection; `lambda ∈ [0,1]` (default 0.7 favouring relevance); requires a distance function (`Cosine | Euclidean | DotProduct`) and a query vector.
- **Score normalizer** as a *separate* module — used only when calibrated fusion is desired (not for RRF).

The architectural insight is the *separation*: rerankers are first-class strategies, not bolted onto the retrieval function. Adding a new fusion strategy is a new struct implementing a `Reranker` trait — see helix `reranker/fusion/` directory layout (`rrf.rs`, `mmr.rs`, `score_normalizer.rs`) as evidence-of-shape only.

### Why this matters for COS

The roadmap includes a LightRAG dual-level retrieval slice and Engram already plans hybrid FTS5 + future-vector retrieval. The natural temptation is to write a hard-coded "combine BM25 and cosine scores with weight α". That is wrong — score scales are incommensurable, and you cannot tune α robustly across queries. RRF avoids the problem; MMR avoids the redundancy problem when retrieving for prompts (where 5 near-duplicate hits waste budget).

### Clean-room reimplementation contract

1. Cite the original papers in the ADR: Cormack/Clarke/Buettcher 2009 (RRF), Carbonell/Goldstein 1998 (MMR). Do not cite helix.
2. The trait/protocol surface is your design (Python `Protocol` or `ABC`); do not mirror the Rust `Reranker` trait shape.
3. Default `k = 60` for RRF is *from the paper*, not from helix. Default `lambda = 0.7` for MMR is also paper-canonical.

### Effort

1 PW including unit tests with synthetic mixed-source ranked lists.

---

## E.3 — Hoisted-embedding / IO-continuation pattern

### Pattern

Two related ideas:

1. **Static (compile-time): hoist all embedding/network calls out of the transaction.** The query compiler detects calls to an `Embed(…)`-like function and emits them *before* opening the transaction. The transaction then operates only on pre-computed embedding tensors. See `helixc/generator/queries.rs:75-100` for evidence-of-shape.
2. **Dynamic (runtime): if a transaction discovers it needs IO mid-flight, return a continuation.** The executor awaits the IO on a separate runtime, then schedules the continuation in a *new* transaction. See `helix_gateway/router/router.rs:31-46` (`IoContFn`).

Together they ensure no transaction ever holds a writer lock across a network round-trip.

### Why this matters for COS

Any future Engram crystallizer pipeline that wraps an LLM call inside a "session of changes that must commit together" needs this. The Python equivalent is more straightforward (no LMDB writer lock to release), but the *discipline* of separating IO from the transaction-scoped section is the right pattern. It also generalizes: any agent operation that combines a memory mutation with an LLM call should structure as (read-tx → close → LLM → write-tx), not (open-tx → LLM → write).

### Clean-room reimplementation contract

1. Implement as a Python context-manager / `async with` decorator pattern; do not mirror `IoContFn`'s Rust closure-based design.
2. Document the *requirement* in the ADR ("crystallization MUST NOT hold a SQLite write transaction across an LLM call"), then derive the implementation from the requirement.

### Effort

1–2 PW including a regression test that asserts no SQLite write txn is held across an `await llm.complete()`.

---

## E.4 — Compiled-DSL contract (NOT recommended for adoption today)

Pattern: typed schema declaration + queries → static analysis → emitted handler functions → linked into the server binary. Three properties together: (a) no `eval(string)` surface, (b) every query parameter has a typed binding, (c) every return shape is a known struct.

Why it is **not** advocated today: Engram's surface is Python+MCP. Adding a DSL increases the attack surface and the learning curve. The pattern would only matter if COS pivots to expose a typed agent-facing query API beyond the flat `mem_*` verbs — and even then, the typed-ADT MCP surface (Primitive #1) covers most of the same security argument at a fraction of the cost.

Effort if adopted: 6–10 PW.

---

## E.4.5 — Sidebar: upstream HNSW default-clamp inconsistency (NOT a COS roadmap item)

Upstream observation only (HelixDB has a default-clamp inconsistency in `vector_core.rs:48-61` — see annex B §B.5: `HNSWConfig::new` default `ef=768` is silently clamped to `[10, 512]`). Not a COS roadmap item — Engram retains SQLite (annex A §A.4) and HelixDB is REJECT runtime. If AGPL disposition ever reverses, file upstream with HelixDB. Recorded as a footnote per cluster-D claim-quality ruling (2026-05-11): reframed from "test a clean-room reimplementation should catch" to upstream-only observation, because the bug has zero relevance to COS unless we adopt HelixDB's HNSW — which we are NOT.

## E.5 — Filter-aware HNSW

Pattern: vector index search consults a filter callback *during* the level-walk, not as a post-filter. For selective filters this preserves recall; for cheap filters it costs little. See `vector_core.rs:166-217` and `:312-381` for evidence-of-shape.

Why it is **not** advocated today: COS does not own a vector index. If/when we ship one (clean-room HNSW or, more realistically, an existing Apache-2.0 implementation like `usearch` or `hnsw_rs` v0.x), this is the *contract* we want, not the *implementation* we want.

Effort: 3–4 PW for a clean-room HNSW. Effort 0 if we adopt an existing permissively-licensed index (just write the filter-aware-search adapter).

---

## E.6 — Two-way inverted index (forward + reverse postings)

Pattern: alongside the standard `term → [postings]` map, maintain `doc_id → [terms]`. Makes deletes term-local instead of full-scan. See `bm25.rs:21-25` for the schema.

Why it is **not** advocated today: FTS5 already does this internally. Only relevant if we ever replace FTS5 — and we have no reason to.

---

## E.7 — Single-writer / N-reader worker pool

Pattern: `flume::bounded` channels, exactly-one writer worker dedicated, N reader workers core-pinned, write/read routing decided by a `HashSet<String>` populated at startup from `#[handler(is_write)]` annotations. See `worker_pool/mod.rs:21-100`.

Why it is **not** advocated today: COS has no equivalent shared-mutable-backend bottleneck. Engram + SQLite WAL handle the concurrency we have. Useful template if a future COS subsystem hosts agents against a shared backend.

---

## E.8 — LMDB-everything substrate (anti-recommendation)

Pattern: one mmap-backed ACID environment holds graph, vector, FTS, secondary indices, and metadata. See `storage_core/mod.rs:48-68`.

Why this is **anti-recommended** for COS: SQLite is correct for our scale, ergonomics, observability, and operator experience. The mmap-substrate is the right answer if you need an OLTP database; it is the wrong answer if you need a memory layer for an agent OS. Do not even consider porting this pattern.

---

## E.9 — Compile-time inventory pattern

Pattern: handlers self-register via `inventory::submit!(…)` at static-init time; binary collects them at startup with zero registration code. Pure Rust pattern.

Not applicable to Python: Python does the equivalent with module-import side effects (e.g. decorators that populate a registry). Already used in COS skill discovery.

---

## E.10 — Engram persistence

Per the task brief, the consolidated ranked list above is saved to engram via `mem_save` with topic_key `tech-radar/helix-db/primitives`, type `pattern`, scope `project`. See bottom of session for confirmation.

---

## E.11 — Final clean-room reminders

Across all primitives:

1. **No code copy.** Not even one-liners, not even constants like `k=60` cited *from helix* (cite the paper instead).
2. **No identifier reuse.** Rename everything to the COS verb space.
3. **No file-layout mirroring.** Place the Python equivalents where they fit COS conventions, not where HelixDB places the Rust ones.
4. **Every adoption must have an ADR** under `docs/architecture/adr/` that names this annex, names the helix file refs *as evidence the design exists*, and explicitly states that the implementation was written from first principles.
5. **Pre-commit license-audit** required on any PR adding `helix`-pattern code: `git diff` must contain zero strings copied from `.cognitive-os/external-source-cache/helix-db/`.
