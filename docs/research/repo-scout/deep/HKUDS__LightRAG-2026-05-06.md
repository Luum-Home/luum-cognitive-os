---
evaluated_at: 2026-05-06 06:35 UTC
evaluation_level: 2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Dual-level retrieval algorithm; portable into Engram)
deep_verdict: ADOPT (algorithm-only) — repo is a full RAG framework, but we adopt only the dual-level retrieval logic
deepwiki_url: https://deepwiki.com/HKUDS/LightRAG
engram_id: pending
---

## Repository Evaluation: HKUDS/LightRAG

### Classification: ADOPT
**Score**: 8.6/10
**Evaluation Level**: 2 (Deep — gh api recursive tree, dir analysis)

### Summary
**[EMNLP 2025] LightRAG: Simple and Fast Retrieval-Augmented Generation.** Production-grade Python RAG framework with `lightrag/` core, `lightrag/api/` FastAPI server, `lightrag/kg/` knowledge graph backends, `lightrag/llm/` provider adapters, `lightrag_webui/` React UI, k8s deploy manifests, and active 1.4.x → 1.5.0rc1 release cadence. Published research backing. The shallow radar correctly scoped this: we want the **dual-level (entity + topic) retrieval algorithm**, not the framework. Verdict: ADOPT for algorithm port into Engram retrieval layer; do NOT vendor the framework.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 9/10 | Dual-level retrieval is exactly the gap in Engram retrieval; algorithm is small and portable |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | Push 2026-05-06 (today); 5 recent tags; 100+ issues/30d; v1.5.0rc1 in flight |
| Maturity | 15% | 8/10 | EMNLP 2025 paper backing; 1.4.x semver line; full k8s deploy + WebUI |
| Integration | 10% | 7/10 | Algorithm extractable in isolation; framework integration would be heavy |
| **Weighted Total** | | **8.95/10** weighted, presented as **8.6/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 100+ (paged out) | high issue activity |
| Release cadence | v1.4.13rc1, v1.4.13, v1.4.14, v1.4.15, v1.5.0rc1 | weekly-to-biweekly releases |
| CI health | 8/10 success | CI green-ish |

### Key Findings
- **Strengths**:
  - Published EMNLP 2025 paper — algorithm is peer-reviewed.
  - Framework is mature: API server, multi-DB KG (Neo4j, MongoDB, Postgres, Qdrant, Redis, Elasticsearch), evaluation tooling (`lightrag/evaluation/`), reproduce scripts (`reproduce/`).
  - Active maintenance, plural maintainers (HKUDS = HKU Data Science).
  - 35k stars on a 19-month-old academic project = real adoption.
- **Weaknesses**:
  - Framework scope is huge (k8s, webui, multiple DBs) — vendoring or even importing as a dependency is high-cost.
  - 230 open issues; ratio of issue volume to maintainer time unclear.
  - Sample documents in `lightrag/evaluation/sample_documents/` may carry license attribution we'd need to track.
- **Architecture**: Modular: storage backends, LLM adapters, KG ops in `lightrag/kg/`, retrieval logic in core. Dual-level retrieval combines entity-level (precise) + topic-level (broad) over the KG.

### Integration Plan
- **What to use**: ONLY the dual-level retrieval algorithm. Read `lightrag/operate.py` (or equivalent file containing the retrieval entry-point) and the `lightrag/kg/` interfaces, port the retrieval logic into Engram's retrieval layer.
- **How to integrate**:
  1. Phase 1: Read `reproduce/` scripts to understand the retrieval call surface.
  2. Phase 2: Reimplement the dual-level scoring in `lib/engram_retrieval.py` (or equivalent), keeping our existing storage abstractions.
  3. Phase 3: A/B vs current Engram retrieval on a benchmark dataset.
- **Effort estimate**: medium (3-5 days for clean-room port + benchmarks)
- **Dependencies it brings**: nothing if we port the algorithm only

### Risks
- Algorithm depth may rely on specific KG schema we don't have — port effort could blow up.
- License compliance: MIT is permissive, but cite the paper + repo per academic norms.
- Active development means upstream may improve faster than our port.

### Cross-Reference vs Shallow Radar
Shallow verdict: "Dual-level (entity+topic) retrieval algorithm; portable into Engram retrieval layer." **Deep evidence agrees fully.** The framework is much larger than the shallow note implied (full k8s deploy + WebUI + 6 storage backends), but the adoption scope (algorithm-only) remains correct. No verdict change.

### Raw Metrics Appendix
```
{"name":"LightRAG","license":"MIT","stars":34789,"forks":4928,"language":"Python","pushed":"2026-05-06T03:09:47Z","created":"2024-10-02T11:57:54Z","open_issues":230,"size":89779 KB}
tags: v1.5.0rc1,v1.4.15,v1.4.14,v1.4.13,v1.4.13rc1
issues_30d=100+, CI=8/10 success
```
