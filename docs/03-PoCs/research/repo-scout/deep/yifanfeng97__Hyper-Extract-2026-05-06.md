---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/yifanfeng97/Hyper-Extract
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: yifanfeng97/Hyper-Extract

### Classification: ASSESS
**Score**: 8.05/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: memory-graph-rag  •  **Surface role**: library

### Summary
Transform unstructured text into structured knowledge with LLMs. Graphs, hypergraphs, and spatio-temporal extractions — with one command.

**Verdict rationale**: Apache-2.0 (verified via LICENSE) Python hypergraph extraction from text. Direct memory-graph-rag relevance — small algorithm, harvestable into Engram graph layer.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 6/10 | hypergraph extraction; harvest patterns |
| License | 25% | 10/10 | Apache-2.0 |
| Activity | 20% | 10/10 | last push 2026-04-30T02:50:53Z |
| Maturity | 15% | 7/10 | 835★ / 89 forks / 2 recent tags |
| Integration | 10% | 7/10 | library |
| **Weighted Total** | | **8.05/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 0 | dormant issues |
| Release cadence | 2 recent tags | 2 recent tags |
| CI health | last 10 runs | CI green (10/10) |

### Key Findings
- **License**: Apache-2.0
- **Stars / activity**: 835★, last push 2026-04-30T02:50:53Z
- **Default branch**: main
- **Topics**: ai, ai-agents, cli, hypergraph, information-extraction, knowledge, knowledge-graph, llm, python, rag
- **Notes**: 
- LICENSE file = Apache-2.0; gh API NOASSERTION is a classifier miss

### ADR-187 Source-Level Proof Pack (partial — supports ASSESS verdict, not adopt)

Files cited (read directly via `gh api .../contents/<path>`):

- README.md:40–95 — extraction CLI: extract → query → visualize → incrementally supplement
- LICENSE — Apache-2.0 (verified by direct file read; gh API NOASSERTION is classifier miss)

**What still missing for an adoption ADR**: COS-fit matrix vs ADR-172 surfaces (lifecycle / doctrine / audit / hook / agent rendering); reversibility plan; integration boundary (read-only vs read-write into COS artifacts); 30/60/90-day falsifiable success criteria. These belong in a separate `ADR-XXX-surface-5-adopt-Hyper-Extract.md` per ADR-187 §Decision.

### Integration Plan
- **What to use**: hypergraph extraction; harvest patterns
- **Effort**: medium (library import)
- **Blocking**: none — adopt or reject directly

### Risks
- **License compatibility**: permissive — clean
- **Surface-5 gate** (ADR-173/187): not applicable
- **Theme drift**: low
- **Star-inflation flag**: no

### Cross-References
- Parent radar: `docs/06-Daily/reports/external-tools-radar-2026-05-06.md`
- Sister batch (tier-1 top-22): wrote to `docs/03-PoCs/research/repo-scout/deep/`
- ADR-173 (research gate): `docs/02-Decisions/adrs/ADR-173-surface-5-research-gate.md`
- ADR-187 (proof contract): `docs/02-Decisions/adrs/ADR-187-surface-5-adoption-proof-contract.md`

### Raw Metrics
<details>
<summary>gh api JSON (key fields)</summary>

```json
{
  "archived": false,
  "created_at": "2026-01-07T09:44:41Z",
  "default_branch": "main",
  "description": "Transform unstructured text into structured knowledge with LLMs. Graphs, hypergraphs, and spatio-temporal extractions \u2014 with one command.",
  "forks": 89,
  "full_name": "yifanfeng97/Hyper-Extract",
  "homepage": "https://yifanfeng97.github.io/Hyper-Extract/",
  "language": "Python",
  "license": "NOASSERTION",
  "name": "Hyper-Extract",
  "open_issues": 0,
  "pushed_at": "2026-04-30T02:50:53Z",
  "stars": 835,
  "topics": [
    "ai",
    "ai-agents",
    "cli",
    "hypergraph",
    "information-extraction",
    "knowledge",
    "knowledge-graph",
    "llm",
    "python",
    "rag"
  ]
}
```

</details>
