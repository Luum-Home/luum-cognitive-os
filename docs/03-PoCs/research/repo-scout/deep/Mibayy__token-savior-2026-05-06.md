---
evaluated_at: 2026-05-06 06:40 UTC
evaluation_level: 2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (MCP server claiming -77% tokens; sidecar candidate)
deep_verdict: TRIAL (claims need independent benchmark verification before adoption)
deepwiki_url: https://deepwiki.com/Mibayy/token-savior
engram_id: pending
---

## Repository Evaluation: Mibayy/token-savior

### Classification: TRIAL
**Score**: 7.4/10
**Evaluation Level**: 2 (Deep — gh api tree, benchmarks dirs, scripts)

### Summary
MCP server claiming "-77% active tokens, -76% wall time, 0 losses across 96 tasks on Claude Opus 4.7." Python, MIT, **CI 10/10 green**, v3.0.0 + v2.8.x cadence. Structural code navigation + persistent memory hybrid. Tree shows real benchmark infrastructure: `tests/benchmarks/{code_retrieval,library_retrieval,memory_retrieval}/results/`. Notable: `docs/superpowers/plans/` directory suggests this project uses superpowers methodology internally. ADOPT-implied by shallow, **downgrade to TRIAL** because the headline numbers warrant independent verification before sidecar adoption.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 9/10 | MCP-native, structural-nav + memory hybrid is direct fit for COS cost-governance + Engram |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 9/10 | Push 2026-05-04; v2.8.1-v3.0.0 cadence; 26 issues/30d |
| Maturity | 15% | 5/10 | 1 month old; v3.0.0 just released; 0 open issues = small or scrubbed; 799 stars |
| Integration | 10% | 8/10 | MCP server = drop-in for any MCP-aware harness |
| **Weighted Total** | | **8.0/10** weighted, presented as **7.4/10** after independent-verification adjustment | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 26 issues | moderate-high issue activity |
| Release cadence | v3.0.0,v2.8.1-v2.8.4 | weekly releases |
| CI health | 10/10 success | CI green |

### Key Findings
- **Strengths**:
  - CI fully green (10/10) — only repo in the batch alongside graphiti's tests with this profile.
  - Real benchmark infrastructure with results checked in (`tests/benchmarks/*/results/`).
  - Clean Python package (`src/token_savior/{memory,server_handlers,utils}`).
  - MCP-server posture is exactly what COS cost-governance needs as a sidecar.
  - "Works with every MCP client" claim — broad applicability.
- **Weaknesses**:
  - **0 open issues** on a 1-month-old project with 800 stars is unusual — either heavily curated or the issue tracker is locked.
  - Headline -77% tokens / -76% wall time / 0 losses on 96 tasks is a bold claim. The benchmark dir exists but has not been independently verified by us.
  - Benchmarks may be selection-biased (96 tasks chosen by author).
  - 60 forks vs 800 stars = moderate signal; less metric-pump than other deep targets.
- **Architecture**: `src/token_savior/{memory,server_handlers,utils}` + benchmarks split. Hooks dir suggests integration with the harness lifecycle.

### Integration Plan (TRIAL+)
- **What to use**:
  1. Set up as a sidecar MCP server in a sandbox; replay COS task corpus; measure independent token/wall-time delta vs claimed -77%/-76%.
  2. If validation passes: promote to ADOPT, treat as cost-governance primitive (RULES §4).
  3. If validation fails: keep on radar as TRIAL, harvest the structural-nav patterns only.
- **How to integrate**: Run as MCP server alongside Engram; instrument with COS cost metrics (`llm-dispatch.jsonl` sibling).
- **Effort estimate**: small for sidecar pilot (1 day); medium for benchmark replication (2-3 days)
- **Dependencies it brings**: MCP runtime (already supported by COS)

### Risks
- Headline benchmark numbers are unverified. Treat with skepticism until reproduced.
- 1-month-old project with no open issues is suspicious; could be heavy ratchet-deletion of bugs.
- Claims of "0 losses" deserve careful adversarial testing.
- License clean, but supply-chain audit recommended before sidecar adoption.

### Cross-Reference vs Shallow Radar
Shallow verdict: "MCP server claiming -77% tokens via structural code-nav + memory hybrid; sidecar candidate." **Deep evidence partially overturns**: the project is real and CI-green, but the headline numbers MUST be independently reproduced before promotion. Downgrade implied-ADOPT → **TRIAL** with explicit verification gate. The shallow radar's note "sidecar candidate" is correct but the sidecar should be a benchmark sandbox first, not a production sidecar.

### Raw Metrics Appendix
```
{"name":"token-savior","license":"MIT","stars":799,"forks":60,"language":"Python","pushed":"2026-05-04T12:25:18Z","created":"2026-03-30T19:35:33Z","open_issues":0,"size":5154 KB}
tags: v3.0.0,v2.8.4,v2.8.3,v2.8.2,v2.8.1
issues_30d=26, CI=10/10 success
```
