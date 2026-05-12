---
title: Memory Layer Evolution SDD
status: sdd-started
date: 2026-05-08
source_index: docs/reports/external-tools-radar-INDEX.md
source_reports:
  - docs/reports/cross-check-A-memory-2026-05-08.md
related_tools: [Graphiti, LightRAG, HippoRAG, MIRIX, DSPy]
---

# Memory Layer Evolution SDD

## SDD kickoff

Wave 2 has started as SDD change `memory-layer-evolution`. The executable plan
lives at `.cognitive-os/plans/architecture/memory-layer-evolution-wave2.md`.
Slice 0 benchmark substrate is implemented. Engram schema/retrieval
defaults stay unchanged until Slice 1 explicitly preserves `strategy=current`
compatibility and passes the benchmark gate.

## Benchmark-local Wave 2 modes

Slice 1-4 strategy modes are implemented in the benchmark harness only:
`temporal-local`, `graph-path-local`, `dual-level-local`, and
`memory-class-local`. They prove the intended deltas without mutating Engram
storage or changing production defaults.

## Runtime opt-in port: M1 + M3

The first runtime port intentionally stops at M1 + M3 and keeps
`strategy=current` unchanged:

- M1: `EngramLifecycle.search(..., retrieval_strategy="wave2-m1-m3")` applies
  temporal validity and supersession-aware reranking. Observations with open
  `valid_to` or accepted `supersedes` source edges receive a current boost;
  observations with closed `valid_to` or accepted `supersedes` target edges
  receive a stale penalty.
- M3: `EngramGraphWalker.support_chains(...)` returns bounded relation paths
  from the search seed set to retrieved targets. The runtime annotates results
  with `support_chain` and a `wave2_score` only when the flag is explicitly
  enabled.

Activation is non-default through either:

```python
EngramLifecycle().search("query", retrieval_strategy="wave2-m1-m3")
```

or:

```bash
COS_ENGRAM_RETRIEVAL_STRATEGY=wave2-m1-m3
```

`None`, empty, and `current` preserve the prior payload and ordering.

## Goal

Design the Wave 2 memory bundle before touching Engram or Cognee code. The
radar proposes four related imports:

1. Graphiti-style temporal validity schema.
2. LightRAG-style dual-level retrieval scoring.
3. HippoRAG-style Personalized PageRank for multi-hop graph retrieval.
4. MIRIX-style memory class overlay.

These should be one coherent change, not four independent migrations.

## Non-goals

- Do not replace Engram wholesale with Graphiti, LightRAG, HippoRAG, or MIRIX.
- Do not add Neo4j/FalkorDB/Kuzu/Postgres/Redis as a default dependency.
- Do not make Cognee or any external memory backend mandatory.
- Do not change public memory claims until benchmark evidence exists.
- Do not reimplement a full RAG framework when COS needs a governed memory
  lifecycle.

## External patterns to evaluate

| Pattern | External source | Proposed COS use | Adoption kind |
|---|---|---|---|
| Temporal validity windows | Graphiti | Add `valid_from` / `valid_to` or equivalent to memory relations/observations. | schema-port |
| Episodes/provenance | Graphiti | Preserve raw observation/session as source of derived relation. | schema-port |
| Dual-level retrieval | LightRAG | Combine entity/relation recall with topic/semantic recall. | algorithm-port |
| Personalized PageRank | HippoRAG | Alternative graph walk mode for multi-hop memory retrieval. | algorithm-port |
| Memory class taxonomy | MIRIX | Add orthogonal `memory_class`: semantic, episodic, procedural, working. | schema-port |
| Structured optimization | DSPy | Optional eval harness for memory retrieval prompts/skills, not storage. | dependency-pilot |

## Proposed staged design

### Slice 0 — Benchmark and fixture design

Create a memory retrieval benchmark before changing defaults.

Fixture types:

- temporal contradiction: old decision superseded by newer decision;
- episodic query: "what happened during session X?";
- procedural query: "how do we run Y?";
- semantic query: "what is the current architecture decision for Z?";
- multi-hop query: decision -> ADR -> implementation file -> test.

Baseline:

- current FTS5 search;
- current graph walker BFS;
- current Cognee optional path if available.

### Slice 1 — Additive schema

Add fields without changing default behavior:

```text
valid_from       nullable timestamp
valid_to         nullable timestamp
memory_class     nullable enum: semantic|episodic|procedural|working
source_episode   nullable reference to raw observation/session/event
```

Backfill defaults should preserve existing results:

- `valid_from = created_at` when safe;
- `valid_to = superseded_at` when superseded, else null;
- `memory_class` inferred conservatively, with `unknown` or null allowed during
  migration.

### Slice 2 — Retrieval modes behind flags

Add retrieval strategies without changing default:

- `strategy=current`: current FTS5 + BFS behavior.
- `strategy=dual_level`: entity/relation + topic/semantic fusion.
- `strategy=ppr`: current search seed + Personalized PageRank on relation graph.
- `strategy=hybrid`: dual-level seed + PPR rerank.

### Slice 3 — Evaluation and default switch

Only switch defaults if benchmark shows improvement without unacceptable cost or
latency. Required metrics:

- precision@k;
- answer support/source correctness;
- temporal correctness;
- multi-hop success;
- p95 latency;
- token/cost delta;
- migration/runtime failure rate.

## Open design questions

1. Should semantic embeddings be local-only, optional provider-backed, or
   delegated to Cognee when available?
2. Does `memory_class` belong on observations, relations, or both?
3. How should Engram’s persistent memory privacy classes interact with
   `memory_class=working`?
4. Can we implement PPR without adding a heavy graph dependency?
5. What is the rollback if schema migration succeeds but retrieval quality
   regresses?

## Acceptance criteria before code

- A benchmark fixture plan is written and reviewed.
- Adoption kind is declared for every external pattern.
- Migration/backfill/rollback are specified.
- Public claims remain unchanged until benchmark evidence exists.
- Current retrieval mode remains available after all slices.
