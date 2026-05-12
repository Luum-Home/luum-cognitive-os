---
evaluated_at: 2026-05-06 06:50 UTC
evaluation_level: 2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Reflective text-evolution primitive; pairs with dspy)
deep_verdict: ADOPT — production-ready optimize-anything primitive, tight DSPy integration
deepwiki_url: https://deepwiki.com/gepa-ai/gepa
engram_id: pending
---

## Repository Evaluation: gepa-ai/gepa

### Classification: ADOPT
**Score**: 8.6/10
**Evaluation Level**: 2 (Deep — gh api tree, src/gepa/ + tests/ + adapters inspection)

### Summary
"Optimize prompts, code, and more with AI-powered Reflective Text Evolution." MIT, Python (Jupyter Notebook is the primary language tag — likely from heavy notebook examples), 4.2k★, push 2026-05-06 (today), v0.1.1 latest with patch line v0.0.25 → v0.1.1. **CI 8/10 green.** Multiple production adapters: `dspy_adapter`, `dspy_full_program_adapter`, `generic_rag_adapter`, `mcp_adapter`, `terminal_bench_adapter`, `optimize_anything_adapter`. Active blog with 5 published posts (2026-02 to 2026-04), `gskill/` subproject for skill optimization. Companion to DSPy.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 9/10 | Reflective text evolution = direct fit for prompt/skill optimization; gskill/ subproject specifically targets skill optimization |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | Push today; 5 recent tags in 0.0.x → 0.1.x line; 63 issues/30d |
| Maturity | 15% | 6/10 | v0.1.1 (recent stable); 9 months old; 91 open issues; pre-1.0 |
| Integration | 10% | 8/10 | DSPy adapter + MCP adapter + RAG adapter = drop-in for many COS surfaces |
| **Weighted Total** | | **8.7/10** weighted, presented as **8.6/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 63 issues | high issue activity |
| Release cadence | v0.1.1, v0.1.0, v0.0.27, v0.0.26, v0.0.25 | weekly releases |
| CI health | 8/10 success | CI green-ish |

### Key Findings
- **Strengths**:
  - **`src/gepa/gskill/`** — explicit skill-optimization subproject. Look at `gskill/gskill/{evaluate, mini_swe_agent_config}` for the skill optimizer surface. Direct match for COS auto-skill-generation + skill-rewrite.
  - **Multiple production adapters**: dspy_adapter, dspy_full_program_adapter, generic_rag_adapter, mcp_adapter, terminal_bench_adapter, optimize_anything_adapter, confidence_adapter, anymaths_adapter. The mcp_adapter is especially notable — drop-in optimizer for MCP servers.
  - Real-world example tracks: `examples/{adrs/can_be_late, adrs/cloudcast, aime_math, arc_agi, blackbox, circle_packing, confidence_adapter}` — published examples reduce learning cost.
  - Active blog: 5 posts including "automatically learning skills for coding agents" (2026-02-18) and "gepa at scale with combee" (2026-04-09). Maintainer engagement signal.
  - DSPy bundles GEPA, GEPA bundles DSPy adapter — bidirectional integration.
- **Weaknesses**:
  - Pre-1.0 (v0.1.1) — API may shift.
  - Jupyter Notebook as primary language → heavy notebooks-as-tests/docs that may be brittle.
  - 91 open issues with 9-month-old project = maintainer-load risk.
  - 4.2k stars vs 356 forks ratio = strong stars / weak community contribution.
- **Architecture**: Core in `src/gepa/{core, proposer, strategies, logging, utils}`; adapters per integration target; gskill/ as the skill-specific surface.

### Integration Plan
- **What to use**:
  1. **`gskill/`** subproject — direct adoption target for COS auto-skill-generation and skill-rewrite primitives.
  2. **`mcp_adapter/`** — drop-in optimizer for any MCP-exposed COS skill (Engram, dispatch, etc.).
  3. **`dspy_adapter/` + `dspy_full_program_adapter/`** — bridge for DSPy programs in COS.
  4. **`generic_rag_adapter/`** — composable with the LightRAG/HippoRAG/graphiti retrieval work.
- **How to integrate**: pip install gepa as dependency for any prompt/skill optimization workflow. Use gskill's evaluate harness to optimize specific COS skills.
- **Effort estimate**: medium (3-5 days for first gskill-optimized COS skill pilot)
- **Dependencies it brings**: gepa + (optional) dspy if using dspy_adapter

### Risks
- Pre-1.0 — pin to v0.1.1.
- Optimization can produce unexpected prompt drift; gate-keep with human review.
- Adapter ecosystem may shrink as v1 stabilizes.

### Cross-Reference vs Shallow Radar
Shallow verdict: "Reflective text-evolution primitive for prompts/code; pairs with dspy." **Deep evidence agrees and amplifies**: the `gskill/` subproject is a direct match for COS skill-optimization needs (not just pairing with dspy). The mcp_adapter opens a path to optimize MCP-exposed COS surfaces directly. Verdict ADOPT confirmed.

### Raw Metrics Appendix
```
{"name":"gepa","license":"MIT","stars":4225,"forks":356,"language":"Jupyter Notebook","pushed":"2026-05-06T04:40:19Z","created":"2025-08-05T09:26:27Z","open_issues":91,"size":104011 KB}
tags: v0.1.1,v0.1.0,v0.0.27,v0.0.26,v0.0.25
issues_30d=63, CI=8/10 success
adapters: anymaths, confidence, default, dspy, dspy_full_program, generic_rag, mcp, optimize_anything, terminal_bench
```
