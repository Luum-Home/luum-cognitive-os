---
evaluated_at: 2026-05-06 06:35 UTC
evaluation_level: 2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Personalized PageRank multi-hop recall; small algorithm port)
deep_verdict: ADOPT (algorithm-only) — research-grade framework, port the PPR multi-hop logic
deepwiki_url: https://deepwiki.com/OSU-NLP-Group/HippoRAG
engram_id: pending
---

## Repository Evaluation: OSU-NLP-Group/HippoRAG

### Classification: ADOPT
**Score**: 7.8/10
**Evaluation Level**: 2 (Deep — gh api tree, src/hipporag/ structure)

### Summary
**[NeurIPS 2024] HippoRAG**: novel RAG framework inspired by human long-term memory using **Personalized PageRank over an entity graph** for multi-hop recall. Cleaner Python package layout than LightRAG (`src/hipporag/embedding_model/`, `evaluation/`, `information_extraction/`, `llm/`, `prompts/`, `prompts/dspy_prompts/`, `prompts/templates/`, `utils/`). MIT, NeurIPS-published. Last pushed 2025-09-04 (~8 months stale) — **inactive flag**. Single tag v1.0.0. Adopt the PPR multi-hop algorithm + the `prompts/dspy_prompts/` artifacts as DSPy integration reference.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 9/10 | PPR multi-hop is a known Engram gap; small algorithm + clean code = high port leverage |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 4/10 | Push 2025-09-04 (~8 months stale); inactive but not dead |
| Maturity | 15% | 7/10 | NeurIPS 2024 paper; v1.0.0 tagged; clean package layout; 21 open issues (manageable) |
| Integration | 10% | 8/10 | `src/hipporag/` is a real Python package; clean imports |
| **Weighted Total** | | **7.8/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 1 issue | low issue activity |
| Release cadence | 1 tag (v1.0.0) | infrequent releases |
| CI health | no runs | no CI found |

### Key Findings
- **Strengths**:
  - NeurIPS 2024 publication = peer-reviewed.
  - Clean `src/hipporag/` package layout — easier to reason about than LightRAG.
  - `prompts/dspy_prompts/` shows DSPy integration — bridges nicely with our DSPy adoption (deep target #14).
  - Small, focused codebase relative to LightRAG.
- **Weaknesses**:
  - **8 months without a push** — auto-reject gate (HOLD threshold is 12mo, but this is concerning). Activity score reflects this.
  - No GH Actions; CI signal absent.
  - Single tag; no semver evolution.
  - 3.5k stars vs LightRAG's 35k — smaller community, fewer external eyes.
- **Architecture**: Standard Python `src/` layout. Modules split cleanly: embedding_model, evaluation, information_extraction, llm, prompts, utils. Knowledge graph + PPR scoring is the core.

### Integration Plan
- **What to use**:
  1. Personalized PageRank multi-hop retrieval algorithm — port into Engram retrieval as a sibling option to LightRAG dual-level.
  2. `prompts/dspy_prompts/` — reference for DSPy-based prompt programs (relevant to deep target #14 stanfordnlp/dspy adoption).
- **How to integrate**: Clean-room re-implement the PPR scoring against Engram's existing entity graph schema.
- **Effort estimate**: small-to-medium (2-4 days)
- **Dependencies it brings**: networkx (or similar) for PPR; we may already have this transitively

### Risks
- 8-month stagnation suggests the project may be in maintenance hibernation. Pin to current commit; don't expect upstream improvements.
- Single tag v1.0.0 means no patch-level signal of stability.
- No CI = unknown test health; verify by running `tests/` (if present) before porting.

### Cross-Reference vs Shallow Radar
Shallow verdict: "Personalized PageRank multi-hop recall over entity graph; small algorithm port." **Deep evidence agrees** but adds an activity caveat the shallow note didn't capture: 8 months without commits. Adoption scope unchanged (port the PPR algorithm). Treat as frozen-reference, not active dependency.

### Raw Metrics Appendix
```
{"name":"HippoRAG","license":"MIT","stars":3484,"forks":352,"language":"Python","pushed":"2025-09-04T14:42:42Z","created":"2024-05-23T23:07:16Z","open_issues":21,"size":82222 KB}
tags: v1.0.0
issues_30d=1, CI=none
```
