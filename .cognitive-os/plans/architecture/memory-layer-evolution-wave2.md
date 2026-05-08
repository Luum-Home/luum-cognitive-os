# SDD Plan — memory-layer-evolution

**Status**: explore/propose started — implementation blocked until Slice 0 benchmark fixtures land  
**Date**: 2026-05-08  
**Source design**: [`docs/architecture/memory-layer-evolution-sdd.md`](../../../docs/architecture/memory-layer-evolution-sdd.md)  
**Radar tracker**: [`docs/reports/radar-2026-05-08-implementation-tracker.md`](../../../docs/reports/radar-2026-05-08-implementation-tracker.md)  
**Doctrine**: [`docs/architecture/external-tool-adoption-doctrine.md`](../../../docs/architecture/external-tool-adoption-doctrine.md)  
**Related radar rows**: M1, M2, M3, M4

---

## Intent

Start Wave 2 as a single SDD change named `memory-layer-evolution`.

The memory bundle is intentionally grouped because Graphiti-style temporal
validity, LightRAG-style dual-level retrieval, HippoRAG-style PPR, and
MIRIX-style memory classes all touch the same memory schema/retrieval boundary.
Splitting them into independent changes would create parallel schema migrations
and inconsistent evaluation criteria.

## Doctrine gate

External Tool Adoption Doctrine is already `status: accepted`. This SDD adopts
its core rule:

> Adopt commodity mechanisms; build governance semantics.

Therefore Wave 2 may import schemas/algorithms as **schema-port** or
**algorithm-port**, but Engram lifecycle, privacy classes, portability,
receipts, project scoping, and memory governance stay first-party COS semantics.

## Non-negotiables

- No default Neo4j/FalkorDB/Kuzu/Postgres/Redis dependency.
- No mandatory Graphiti, LightRAG, HippoRAG, MIRIX, Cognee, or DSPy runtime.
- No public claim updates before benchmark evidence exists.
- Current Engram search/retrieval remains available after every slice.
- Schema changes are additive, idempotent, and reversible.
- Privacy/portability classes from ADR-202 remain authoritative.

## Slice 0 — Benchmark and fixtures first

Before code changes to retrieval defaults, create a deterministic benchmark
suite that can fail a proposed memory algorithm.

### Fixture classes

| Fixture | Purpose | Minimum expected proof |
|---|---|---|
| temporal contradiction | Old decision superseded by a newer decision | newer decision ranks above stale decision and exposes source support |
| episodic query | Session-specific recall | answer cites correct session/event evidence |
| procedural query | How-to retrieval | retrieves the current runbook/procedure, not old chat fragments |
| semantic decision query | Current architecture/policy | retrieves accepted ADR/manifest over exploratory notes |
| multi-hop query | decision -> ADR -> implementation -> test | produces supported chain without hallucinated links |

### Baselines

- Current FTS5 search.
- Current graph walker / BFS retrieval.
- Existing optional Cognee path when available, opt-in only.

### Acceptance

- Fixtures are checked into tests, not only described in prose.
- The benchmark reports precision@k, temporal correctness, source support,
  multi-hop success, p95 latency, and token/cost delta.
- Failing benchmark cases become named regression tests before algorithm work.

## Slice 1 — Additive schema

Add nullable fields without changing default behavior:

```text
valid_from       nullable timestamp
valid_to         nullable timestamp
memory_class     nullable enum: semantic|episodic|procedural|working|unknown
source_episode   nullable reference to raw observation/session/event
```

Backfill policy:

- `valid_from = created_at` only when created_at is known and trusted.
- `valid_to = superseded_at` when a supersession relation exists; else null.
- `memory_class = unknown` unless inference is deterministic.

### Acceptance

- Migration is idempotent.
- Rollback/downgrade is documented.
- Existing queries return identical top-k under `strategy=current`.
- No private-content portability class is weakened.

## Slice 2 — Retrieval modes behind flags

Add modes without changing default:

| Strategy | Description | Default? |
|---|---|---:|
| `current` | Current FTS5 + graph walk behavior | yes |
| `dual_level` | entity/relation + topic/semantic fusion | no |
| `ppr` | search seed + Personalized PageRank on relation graph | no |
| `hybrid` | dual-level seed + PPR rerank | no |

### Acceptance

- Each mode can be run on the same benchmark fixtures.
- Mode selection is explicit and observable in reports.
- Any mode failure falls back to `current` without corrupting state.

## Slice 3 — Evaluation and default switch decision

Switching defaults requires evidence, not enthusiasm.

Required evidence:

- better precision@k or source-support score than `current`;
- no temporal correctness regression;
- no unacceptable p95 latency or cost delta;
- no migration/runtime failure rate above agreed threshold;
- rollback tested.

If evidence is mixed, keep `current` as default and ship the improved mode as
manual/opt-in only.

## First implementation target

The next coding task is **Slice 0 only**:

1. Add a benchmark manifest under `manifests/memory-retrieval-benchmark.yaml`.
2. Add deterministic fixtures under `tests/fixtures/memory_retrieval/`.
3. Add a non-mutating benchmark runner under `scripts/cos-memory-benchmark`.
4. Add tests proving the runner catches stale temporal answers and unsupported
   multi-hop chains.

Do not touch Engram storage schema or retrieval defaults until Slice 0 is green.

## Definition of Done for SDD start

- [x] Doctrine status verified as accepted.
- [x] Design doc exists and is linked.
- [x] SDD plan created with Slice 0/1/2/3 ordering.
- [x] Radar tracker updated to show SDD started.
- [ ] Slice 0 benchmark implementation merged.
- [ ] Slice 1 schema migration merged.
- [ ] Slice 2 retrieval modes merged.
- [ ] Slice 3 default decision recorded.
