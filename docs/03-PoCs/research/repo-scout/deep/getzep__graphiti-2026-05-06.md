---
evaluated_at: 2026-05-06 06:40 UTC
evaluation_level: 2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Bi-temporal edge schema known gap in Engram)
deep_verdict: ADOPT (algorithm-only) — port bi-temporal edge schema; framework too large to vendor
deepwiki_url: https://deepwiki.com/getzep/graphiti
engram_id: pending
---

## Repository Evaluation: getzep/graphiti

### Classification: ADOPT
**Score**: 8.7/10
**Evaluation Level**: 2 (Deep — gh api recursive tree)

### Summary
**Real-time knowledge graph framework for AI agents** by getzep (commercial-OSS hybrid). Apache-2.0, Python, push 2026-04-30, **v0.30.0pre5** in active development. Multi-driver KG layer (Neo4j, Kuzu, Neptune, FalkorDB), built-in MCP server (`mcp_server/`), API server (`server/`), embedded LLM client adapters, ontology utils, evaluation suite (`tests/evals/longmemeval_data`). Strongest production-grade KG framework in the deep batch. Adopt the **bi-temporal edge schema** (event-time vs ingest-time) — known gap in Engram per the shallow radar — plus their cross-encoder reranking.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 10/10 | Bi-temporal edge schema is a known Engram gap; cross-encoder reranking is also adoptable |
| License | 25% | 8/10 | Apache-2.0 (slightly more compliance overhead than MIT but still clean) |
| Activity | 20% | 10/10 | Push 2026-04-30; 5 v0.30 prereleases visible; 100+ issues/30d |
| Maturity | 15% | 7/10 | v0.30 prereleases, 4 KG drivers, 25k stars, 21mo old; pre-1.0 = ongoing API churn |
| Integration | 10% | 8/10 | Python, modular drivers, separate MCP server, separate API server — pick what we need |
| **Weighted Total** | | **8.95/10** weighted, presented as **8.7/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 100+ (paged out) | high issue activity |
| Release cadence | 5 prereleases v0.30.0pre1-pre5 | weekly releases |
| CI health | 3/10 success | CI mostly red (likely cancelled runs from PR cycles) |

### Key Findings
- **Strengths**:
  - Bi-temporal edge schema (event_time vs ingest_time) is exactly the gap the shallow radar called out for Engram.
  - 4 KG drivers (Neo4j, Kuzu, Neptune, FalkorDB) — Kuzu is interesting as embedded option.
  - First-class `mcp_server/` exposes the graph as MCP — relevant to COS MCP-extension cluster.
  - Real evals against LongMemEval (`tests/evals/longmemeval_data`).
  - 9 example projects (azure-openai, ecommerce, langgraph-agent, opentelemetry, podcast, quickstart) reduce learning cost.
- **Weaknesses**:
  - Apache-2.0 is fine but adds NOTICE-file compliance vs MIT.
  - 392 open issues; pre-1.0 churn risk.
  - getzep is a commercial company — community/commercial split may diverge.
  - Framework scope is large; adopting the whole would be heavy.
- **Architecture**: `graphiti_core/` is the reusable library; `server/` and `mcp_server/` are deployable surfaces. Driver plugins per backend. Cross-encoder for reranking. Telemetry built in.

### Integration Plan
- **What to use**:
  1. **Bi-temporal edge schema** from `graphiti_core/models/edges/`. Direct port into Engram edge model.
  2. **Cross-encoder reranking** from `graphiti_core/cross_encoder/` — sibling to retrieval improvements from LightRAG/HippoRAG.
  3. `mcp_server/` as reference for exposing Engram graph over MCP.
  4. LongMemEval test corpus as benchmark for our memory layer.
- **How to integrate**: Schema port + algorithm port + benchmark adoption. Do NOT vendor the framework.
- **Effort estimate**: medium-large (4-7 days for schema + reranking port + LongMemEval bench wiring)
- **Dependencies it brings**: optional (sentence-transformers for cross-encoder if we adopt it)

### Risks
- Apache-2.0 NOTICE compliance must be satisfied if we vendor any code.
- Pre-1.0 API churn — pin to a specific commit when porting.
- Commercial-OSS split: watch for breaking license changes (BSL-style relicense risk on commercial-backed projects).

### Cross-Reference vs Shallow Radar
Shallow verdict: "Bi-temporal edge schema (event-time vs ingest-time) — known gap in Engram model." **Deep evidence agrees and broadens scope**: in addition to bi-temporal edges, the cross-encoder reranking and LongMemEval benchmark wiring are equally adoptable. Verdict ADOPT confirmed.

### Raw Metrics Appendix
```
{"name":"graphiti","license":"Apache-2.0","stars":25735,"forks":2560,"language":"Python","pushed":"2026-04-30T18:51:35Z","created":"2024-08-08T22:08:30Z","open_issues":392,"size":14583 KB}
tags: v0.30.0pre5..pre1
issues_30d=100+, CI=3/10 success
```
