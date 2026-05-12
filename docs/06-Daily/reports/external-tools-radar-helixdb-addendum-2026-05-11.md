---
report_type: external-tools-radar-addendum
subject: HelixDB/helix-db
generated_at: 2026-05-11
status: reject-runtime / trial-patterns
pattern_lane_history:
  - 2026-05-11 initial: HOLD pattern-only
  - 2026-05-11 reconciled: TRIAL-PATTERNS (cluster-B coherence audit; annex E identifies 3 primitives, clean-room 3-5 PW combined; consistent with TRIAL-PATTERNS doctrine in docs/04-Concepts/architecture/external-tool-adapter-taxonomy.md; iFixAi Phase 12 precedent)
related_adrs: [ADR-065, ADR-247, ADR-254]
source_artifacts:
  - docs/03-PoCs/research/repo-scout/deep/HelixDB__helix-db-2026-05-11.md
related_docs:
  - docs/04-Concepts/patterns/ecosystem-tools.md
  - docs/05-Methodology/root/blocked-tools.md
  - manifests/external-tools-adoption.yaml
  - rules/license-policy.md
  - docs/04-Concepts/architecture/external-tool-adoption-doctrine.md
  - docs/04-Concepts/architecture/external-tool-adapter-taxonomy.md
  - docs/06-Daily/reports/cross-check-A-memory-2026-05-08.md
  - docs/04-Concepts/architecture/memory-layer-evolution-sdd.md
---

# External Tools Radar HelixDB Addendum — 2026-05-11

## Decision

Add [HelixDB/helix-db](https://github.com/HelixDB/helix-db) to the tech radar as **REJECT for runtime/dependency adoption** and **TRIAL-PATTERNS** for clean-room schema and DSL study (promoted from HOLD on 2026-05-11 — see Recommendation §2 for rationale). The blocking signal is license: AGPL-3.0 is on the BLOCK list in `rules/license-policy.md`, and the project is positioned as the AGPL "Lite" half of an open-core split with a closed "Enterprise" tier — the same shape that produced past SSPL/ELv2 traps for downstream adopters.

The non-license signals are otherwise interesting (Rust, LMDB-backed unified graph+vector store, compiled type-safe HelixQL, built-in embeddings, native MCP surface, YC/Nvidia/Vercel funding, 4.4k stars, active releases). That is why it does not get a clean REJECT-and-forget verdict — only the dependency lane is closed; the pattern lane stays open.

## Adoption kind (per `external-tool-adapter-taxonomy.md`)

| Lane | Adoption kind | Status |
|---|---|---|
| Dependency / library embed | `rejected` | License-blocked (AGPL-3.0). |
| Operator-installed external service | `rejected` | AGPL §13 network-use risk on default paths; not worth legal review when alternatives exist. |
| Schema port (graph+vector primary types, vectorize-this-field annotation) | `trial-patterns` | Reference idea for future Engram graph-memory work; promoted from `pattern-only` on 2026-05-11 (cluster-B coherence audit). |
| Algorithm port (HelixQL compiled-query lowering) | `trial-patterns` | Clean-room only; HelixQL itself is AGPL. Promoted from `pattern-only` on 2026-05-11. |
| Test-data vendor | not applicable | No fixture utility identified. |
| Runtime adapter candidate | not applicable | Blocked upstream of any adapter work. |

Net: this entry should land in the radar under EVALUATE/REJECT with a pointer to the deep eval, and in `docs/05-Methodology/root/blocked-tools.md` under license-blocked when `/radar-update --apply` next runs (this addendum does **not** modify those files — that is out of scope per the task brief).

## Bidirectional axis — verdict vs Engram + current memory stack

Following the Phase 3 cross-check shape (`docs/06-Daily/reports/cross-check-A-memory-2026-05-08.md`):

| Compared against | Verdict | Rationale + concrete COS refs |
|---|---|---|
| **Engram** (the project's persistent memory) | **MEJOR_NUESTRO (governance) / NO_COMPARABLE (storage tier)** | HelixDB is a storage substrate. Engram owns the governance product surface (project scoping, privacy classes, receipts, portability, decay) — see `docs/04-Concepts/architecture/memory-layer-evolution-sdd.md` and `docs/04-Concepts/architecture/external-tool-adoption-doctrine.md` Domain matrix row "Temporal memory / knowledge graph". HelixDB does not displace Engram; it would only ever sit underneath, which the license forbids. |
| **Cognee** | **NO_COMPARABLE** | Different layers: Cognee = KG+RAG framework, HelixDB = DB. |
| **ChromaDB** | **MEJOR_EXTERNO on paper / MEJOR_NUESTRO operationally** | Unified graph+vector primary types are arguably cleaner than Chroma's vector-first posture, but Chroma is Apache-2.0 and already integrable; HelixDB's AGPL closes the operational door. |
| **Graphiti** (already on the COS radar as schema-port candidate per doctrine) | **IGUAL on schema ideas** | Both inform the same future Engram graph-memory schema-port. Graphiti is the preferred reference (permissive license per doctrine row); HelixDB is secondary pattern reading only. |
| **LMDB direct** | **N/A** | HelixDB's value-add over raw LMDB is exactly the AGPL-licensed parts (HelixQL + vector indexing). For COS, that value is unreachable. |

Concrete COS-side anchors for any future pattern extraction:

- Engram governance surface: see global protocol described in `~/.claude/CLAUDE.md` (Engram MCP tools) + `docs/04-Concepts/architecture/memory-layer-evolution-sdd.md`.
- Memory cross-check verdict shape: `docs/06-Daily/reports/cross-check-A-memory-2026-05-08.md`.
- Adoption doctrine row this entry maps to: `docs/04-Concepts/architecture/external-tool-adoption-doctrine.md` "Temporal memory / knowledge graph".
- License policy enforcement: `rules/license-policy.md` (AGPL → BLOCK).

## Recommendation

1. **Do not embed, link, or host as a default COS service.** AGPL-3.0 viral terms + open-core split = highest-class license risk for COS.
2. **Keep on the radar as TRIAL-PATTERNS.** Pattern lane promoted from HOLD to TRIAL-PATTERNS on 2026-05-11 after cluster-B coherence audit: annex E identifies 3 primitives with clean-room cost 3-5 PW combined, consistent with TRIAL-PATTERNS doctrine in `docs/04-Concepts/architecture/external-tool-adapter-taxonomy.md`. Precedent: iFixAi (Phase 12) — same shape, TRIAL-PATTERNS posture. The five primitive-extraction candidates in the deep eval (compiled DSL, unified graph+vector schema, LMDB-backed graph+vector layout, MCP-on-the-DB pattern, schema-level embed annotation) are worth referencing when Engram's graph-memory phase needs design inputs; the top 3 in annex E §E.1-E.3 are the trial-patterns targets.
3. **Prefer Graphiti (Apache-2.0) and LightRAG/HippoRAG (per existing doctrine rows) as the primary memory-tier references.** HelixDB is a corroborating data point, not a primary reference.
4. **Re-evaluate only on license change or specific COS need.** Triggers: upstream relicense to Apache/MIT/BSD; or COS commits to a compiled-DSL memory query surface and HelixQL remains the best public example.

## Acceptance criteria

- [x] License verified against `rules/license-policy.md` (AGPL-3.0 → BLOCK).
- [x] Bidirectional verdict computed vs Engram, Cognee, ChromaDB, Graphiti, LMDB.
- [x] Adoption kind assigned per `external-tool-adapter-taxonomy.md` (rejected for dependency/operator-installed; pattern-only for schema/algorithm port).
- [x] Deep eval artifact written at `docs/03-PoCs/research/repo-scout/deep/HelixDB__helix-db-2026-05-11.md`.
- [x] INDEX entry appended under a new Phase 7 section.
- [x] Engram memory saved under topic key `tech-radar/helix-db`.
- [ ] `docs/04-Concepts/patterns/ecosystem-tools.md` + `docs/05-Methodology/root/blocked-tools.md` updates deferred to `/radar-update --apply` (out of scope).

## Rollback / exit path

There is no runtime to roll back — this addendum declines adoption upstream of any code change. The pattern-only lane has no rollback obligation because no code is copied. If a future engineer proposes embedding HelixDB or a HelixDB-derived module, the rollback contract is: refuse at license-gate, point at this addendum, require ADR override + legal sign-off.

## Unknowns / unverified upstream

- Vector index choice (HNSW / IVF / flat) — not confirmed in this pass.
- Concurrency / write throughput under LMDB single-writer at agent-workload rates.
- Helix Enterprise license terms (not on landing page).
- Whether `helix-py` / `helix-ts` SDK packages carry the AGPL or a more permissive client license — needs source verification before any client-only experiment.
