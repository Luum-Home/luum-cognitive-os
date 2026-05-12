---
report_type: repo-scout-deep-analysis
repo: HelixDB/helix-db
evaluated_at: 2026-05-11
classification: REJECT
license: AGPL-3.0
verdict_vs_engram: MEJOR_NUESTRO (governance) / NO_COMPARABLE (raw graph+vector storage tier)
source_artifacts:
  - https://github.com/HelixDB/helix-db
  - https://www.helix-db.com/
related_docs:
  - docs/06-Daily/reports/external-tools-radar-helixdb-addendum-2026-05-11.md
  - rules/license-policy.md
  - docs/04-Concepts/architecture/external-tool-adoption-doctrine.md
  - docs/04-Concepts/architecture/external-tool-adapter-taxonomy.md
  - docs/06-Daily/reports/cross-check-A-memory-2026-05-08.md
---

# HelixDB / helix-db Deep Analysis — 2026-05-11

## Executive classification

**REJECT for dependency / runtime adoption. HOLD as pattern-only reference.**

HelixDB is a young but well-funded (Y Combinator, Nvidia, Vercel) open-source graph+vector database written in Rust, distributed under **AGPL-3.0**. The combination of (a) AGPL viral-network terms, (b) the open-core split between Helix Lite (AGPL) and a commercial Helix Enterprise tier, and (c) the lack of a dual-license/commercial use exemption from the public README makes the project a hard REJECT for any code/binary embedding into COS or COS-managed services. Per `rules/license-policy.md`, AGPL is on the BLOCK list for dependency adoption.

The repository is still worth tracking as a **pattern reference** for: LMDB-backed graph+vector unification, a compiled type-safe query language (HelixQL), built-in embeddings, and an explicit MCP surface. Those design ideas may inform future Engram or memory-tier work via clean-room schema/pattern ports, never via code import.

## Acceptance criteria

1. License posture is verified against `rules/license-policy.md` before any scoring proceeds. AGPL-3.0 is BLOCK.
2. Bidirectional verdict is computed against Engram + COS memory stack (Cognee/ChromaDB) using the Phase 3 vocabulary (MEJOR_NUESTRO / IGUAL / MEJOR_EXTERNO / NO_COMPARABLE).
3. Adoption kind is assigned per `docs/04-Concepts/architecture/external-tool-adapter-taxonomy.md`.
4. Deep eval covers identity, architecture, weighted scoring, primitive extraction candidates, risks, and rollback/exit path.
5. Two artifacts written (this deep eval + the radar addendum) and INDEX appended.

## Evidence sources

- GitHub repository: <https://github.com/HelixDB/helix-db> (snapshot 2026-05-11 via `gh repo view --json`).
- Landing page: <https://www.helix-db.com/>
- Latest release tag: `v2.3.4` published 2026-03-31.
- Existing COS memory cross-check: `docs/06-Daily/reports/cross-check-A-memory-2026-05-08.md`.
- No prior Engram observation for `HelixDB` / `helix-db` was found in this project (mem_search to be confirmed at close).

Network access was used only to fetch the public GitHub metadata JSON and the landing page summary; deeper source-tree forensics (clone, hql-tests, helix-container internals) were **not** performed in this pass and are marked unverified upstream.

## Identity

| Signal | Value |
|---|---|
| Owner / repo | `HelixDB/helix-db` |
| Description | "HelixDB is an open-source graph-vector database built from scratch in Rust." |
| License | **AGPL-3.0** (BLOCK per `rules/license-policy.md`) |
| Primary language | Rust |
| Stars | ~4,419 (2026-05-11) |
| Forks | 235 |
| Created | 2024-11-23 |
| Last push | 2026-05-07 |
| Latest release | `v2.3.4` (2026-03-31) — 171 releases total reported by README scrape (unverified upstream) |
| Default branch | `main` |
| Homepage | https://helix-db.com |
| Funding signals | YC, Nvidia, Vercel (per landing page) |
| Commercial split | Helix Lite (AGPL OSS) / Helix Enterprise (closed, terms not on landing page) |

## One-liner (≤120 chars)

Rust-built graph+vector database with a compiled type-safe query language (HelixQL), LMDB storage, and MCP surface — AGPL.

## Technical architecture summary

Based on README + landing page (unverified upstream beyond the README scrape):

- **Storage engine:** LMDB (memory-mapped, single-writer, copy-on-write B+tree). No RocksDB. No explicit HNSW reference found in the README scrape; vector indexing strategy needs source-level confirmation.
- **Data model:** unified graph + vector as primary primitives; README claims KV, document, relational shapes are also expressible.
- **Query language:** HelixQL — a compiled, type-safe DSL. Queries are compiled (not interpreted at the hot path), which is the project's main performance lever versus general-purpose graph DBs.
- **Workspace:** Rust workspace with crates including `helix-cli`, `helix-container`, `helix-macros`, `hql-tests`.
- **Deployment:** server process via Helix CLI; "Helix Lite" positioned for local/cloud self-host; "Helix Enterprise" closed.
- **Clients:** `helix-ts` (TypeScript SDK) and `helix-py` (Python SDK).
- **AI surface:** built-in embeddings + advertised MCP support (Model Context Protocol). This is the most COS-relevant integration claim.
- **Maturity:** 2,652 commits on `main`, 171 releases reported, but only ~17 months old. API stability is unproven for an AGPL DB intended as durable memory backing.

## Weighted score (repo-scout rubric, advisory)

Using the same weighting shape as prior Phase 4 deep evals (relative, qualitative — no benchmark run was performed):

| Dimension | Weight | Score (0-5) | Notes |
|---|---:|---:|---|
| License compatibility | 25% | 0 | AGPL-3.0 is on the BLOCK list for dependency / runtime embedding. Hard floor. |
| Maturity / API stability | 15% | 2 | 17 months old, 171 releases, no LTS posture. Heavy churn. |
| Architectural fit (graph+vector unified) | 15% | 4 | Strong fit for the Engram graph-memory roadmap conceptually. |
| Operational footprint | 10% | 2 | Server-mode Rust DB. Heavier than the local-first Engram baseline. |
| Ecosystem / community | 10% | 4 | 4.4k stars, YC/Nvidia/Vercel signal, active. |
| Performance posture | 10% | 3 | Compiled queries + LMDB is credible; no first-party benchmark verified here. |
| Integration cost (clients, MCP) | 10% | 3 | Python + TS SDKs + MCP surface lower wiring cost — but irrelevant under license block. |
| Risk surface (license, vendor, fork) | 5% | 1 | AGPL + open-core split = highest risk class for COS. |
| **Weighted total** | 100% | **~2.0/5** | License gate dominates; non-license dimensions average ~3.0/5. |

The non-license average (~3.0/5) is the reason this gets HOLD-as-pattern-only rather than full REJECT-and-forget.

## Classification (ADOPT / TRIAL / ASSESS / HOLD / REJECT)

- **For dependency / runtime / library embedding:** **REJECT.** AGPL-3.0 viral terms incompatible with COS's local-first, Apache/MIT-friendly distribution posture; would taint any COS process that links or remote-calls in an AGPL-defined "network use" sense.
- **For pattern study (clean-room schema/algorithm port):** **HOLD / pattern-only.** Same posture used for AGPL/SSPL/BSL projects in prior phases: no source copying, no derivative work; ideas only, with explicit attribution to the public README.

This split mirrors how COS handled SSPL/AGPL DBs in Phase 2 (see `docs/05-Methodology/root/blocked-tools.md` convention).

## Bidirectional verdict vs current COS memory stack

- vs **Engram** (project's persistent memory; canonical reference `docs/06-Daily/reports/cross-check-A-memory-2026-05-08.md`): **MEJOR_NUESTRO for governance, NO_COMPARABLE for storage tier.** Engram owns lifecycle, privacy classes, project scoping, receipts, and portability — HelixDB owns none of that. HelixDB is a storage substrate; Engram is a governance memory product. They live at different layers.
- vs **Cognee**: **NO_COMPARABLE.** Cognee is a knowledge-graph + RAG framework; HelixDB is a DB. Different layers.
- vs **ChromaDB**: **IGUAL → MEJOR_EXTERNO on paper** for unified graph+vector, but **MEJOR_NUESTRO operationally** because ChromaDB is Apache-2.0 and already adoptable; HelixDB's AGPL closes the door.
- vs **LMDB direct** (which COS could in principle embed itself): HelixDB's value-add over raw LMDB is HelixQL + the vector primitives. Those are exactly the parts an in-house clean-room would have to re-derive — and Engram already has graph patterns documented in `docs/04-Concepts/architecture/memory-layer-evolution-sdd.md`.

Net: HelixDB does not displace anything in the COS stack today, and cannot be embedded.

## Primitive extraction candidates (pattern-only, clean-room)

Worth studying as design references — not as code imports:

1. **Compiled type-safe query DSL pattern.** HelixQL's "compile queries, don't interpret them at the hot path" is a strong pattern for any future first-party COS memory query surface. Compare against current Engram retrieval call shape.
2. **Unified graph+vector primary types.** The schema posture (graph node = vector-carrying entity, not a sidecar collection) is a useful schema-port reference for Engram's temporal-graph evolution alongside Graphiti.
3. **LMDB as the durable substrate for graph+vector.** LMDB has been a recurring shortlist option in the cross-check-A memory work; HelixDB's existence is corroborating signal, not a new idea.
4. **MCP-first surface on a database.** The pattern of "the DB itself exposes MCP tools, not just a client SDK" is interesting for COS's MCP exposure story (see `docs/04-Concepts/architecture/external-tool-adoption-doctrine.md` MCP row).
5. **Built-in embedding function.** A schema-level "vectorize this field" annotation is a pattern worth comparing with Engram's current per-observation embedding flow.

All five are `pattern-only` per the adapter taxonomy. None should produce code copies.

## Integration cost estimate

- **As a dependency:** N/A — blocked by license.
- **As an operator-installed external service** (run separately, COS talks to it over network): theoretically possible but AGPL §13 "network use is distribution" means any COS-bundled adapter that becomes the default path is at risk of triggering source-disclosure obligations on COS itself. This is exactly the boundary `rules/license-policy.md` is designed to keep us away from. Estimate: not worth the legal review hours given the alternative is Engram + (eventual) Graphiti schema-port.
- **As a pattern reference:** ~2 engineer-hours per primitive extraction candidate above, executed under clean-room discipline. Total ~10h for the full set, deferred until Engram graph-memory work needs it.

## Risks

Top risks ranked:

1. **License contamination (HIGH).** AGPL-3.0 on a backing DB is the highest-impact license risk class for a distributed/agent-facing system. Even an opt-in adapter could be read as triggering AGPL §13 obligations if shipped as a default.
2. **Open-core trapdoor (HIGH).** The Helix Lite (AGPL) vs Helix Enterprise (closed) split is the textbook setup for future re-licensing or feature paywalling. Mongo→SSPL and Elastic→ELv2 are the recent precedents.
3. **API churn (MEDIUM).** 17 months old, 171 releases — HelixQL is still moving. Any schema-port done now risks needing re-derivation.
4. **No verified benchmarks (MEDIUM).** Performance claims are uncorroborated in this pass; would need first-party measurement before any operational decision.
5. **Vector indexing strategy unclear (LOW-MEDIUM).** README scrape did not surface HNSW/IVF/PQ choice; vector recall/latency posture is unverified upstream.

## Final recommendation

- Tag HelixDB **REJECT** for runtime/dependency adoption in `docs/05-Methodology/root/blocked-tools.md` territory (this report flags it; the actual ledger update is `/radar-update --apply` work, not this pass).
- Keep it **HOLD / pattern-only** in the radar for clean-room schema and DSL pattern study.
- Revisit only if upstream relicenses to Apache-2.0 / MIT / BSD, **or** if COS's Engram graph-memory work explicitly needs a compiled-DSL reference and HelixQL is still the best public example at that time.

## Unknowns / unverified upstream

- Vector index data structure (HNSW vs IVF vs flat) — not confirmed from README scrape.
- Concurrency model under LMDB single-writer constraint at agent-workload write rates — not measured here.
- Helix Enterprise terms — not on the public landing page.
- DeepWiki page and hql-tests test inventory — not fetched in this pass.
