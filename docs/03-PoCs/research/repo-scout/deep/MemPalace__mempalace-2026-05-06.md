---
evaluated_at: 2026-05-06 06:40 UTC
evaluation_level: 2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Benchmark-led memory system; harvest scoring/eviction patterns)
deep_verdict: ADOPT — direct cross-harness peer to Engram with active benchmark suite
deepwiki_url: https://deepwiki.com/MemPalace/mempalace
engram_id: pending
---

## Repository Evaluation: MemPalace/mempalace

### Classification: ADOPT
**Score**: 8.8/10
**Evaluation Level**: 2 (Deep — gh api tree, plugin manifests, benchmarks dir)

### Summary
"The best-benchmarked open-source AI memory system." Python, MIT, push 2026-05-06 (active right now), v3.3.4 latest, **9/10 CI green**, multi-harness plugin packaging (`.claude-plugin/`, `.codex-plugin/`, `.agents/plugins/`). Direct competitor / sibling to Engram. The benchmarks/ directory + tests/benchmarks/ + claim of "best-benchmarked" makes this the highest-priority memory-system to compare Engram against on equal footing. Cross-harness skill packaging mirrors superpowers + everything-claude-code patterns.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 10/10 | Direct peer to Engram; benchmarks let us calibrate Engram against an active competitor |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | Push today; v3.3.0-3.3.4 cadence; 100+ issues/30d |
| Maturity | 15% | 7/10 | v3.3.x semver; only 1 month old (created 2026-04-05); 524 open issues = high churn |
| Integration | 10% | 8/10 | Cross-harness packaging in place; Python; MCP-friendly |
| **Weighted Total** | | **9.05/10** weighted, presented as **8.8/10** after age/churn adjustment | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 100+ (paged out) | high issue activity |
| Release cadence | v3.3.0-v3.3.4 | weekly releases |
| CI health | 9/10 success | CI green |

### Key Findings
- **Strengths**:
  - **CI 9/10 green** — best CI health in the deep batch among large skill/memory repos.
  - Multi-harness plugin packaging: `.claude-plugin/skills/mempalace/`, `.codex-plugin/skills/{help,init,mine,search,status}/` — concrete reference for COS cross-harness skill emit.
  - Cross-harness skill commands (help/init/mine/search/status) is a sensible minimal skill set for any memory system.
  - benchmarks/ + tests/benchmarks/ + RFCs in `docs/rfcs/` = mature project posture despite young age.
  - Plural backends (`mempalace/backends/`), i18n built in (`mempalace/i18n/`).
  - 51k stars in 1 month is anomalous (metric-pump risk again — consistent with the radar's broader pattern).
- **Weaknesses**:
  - Only 1 month old; v3.3.4 with 5 versions in 30 days = high churn.
  - 524 open issues, 6,746 forks for a 1-month repo = community signal questionable (similar fork-pump pattern to affaan-m and obra).
  - "Best-benchmarked" is a strong claim — verify against actual published numbers before treating as authoritative.
- **Architecture**: Core in `mempalace/`; cross-harness plugin manifests; `integrations/openclaw/`; landing site in `website/`; benchmarks separate from unit tests.

### Integration Plan
- **What to use**:
  1. **Benchmark suite** — port the benchmark runner (or run Engram against the same datasets) to calibrate.
  2. Cross-harness plugin manifests — concrete reference for COS to emit skills across Claude Code + Codex.
  3. `mempalace/instructions/` — meta-prompt patterns for memory operations.
  4. `mempalace/backends/` — plural-backend architecture (compare against Engram backend abstraction).
  5. Skill set (help/init/mine/search/status) — minimal viable memory-skill API.
- **How to integrate**: Pattern adoption + benchmark borrowing. Do NOT depend on mempalace as a library — they will move faster than us.
- **Effort estimate**: medium (3-5 days for benchmark wiring + cross-harness emit pattern adoption)
- **Dependencies it brings**: Python (already in COS); optional benchmark deps

### Risks
- Project is brand new (1 month) and changing daily — pinning is mandatory.
- Star/fork inflation pattern.
- Single org (MemPalace) — bus factor unknown.
- Claim of "best-benchmarked" requires verification before COS mirrors any benchmark methodology.

### Cross-Reference vs Shallow Radar
Shallow verdict: "Benchmark-led memory system; harvest scoring/eviction patterns to compare with Engram." **Deep evidence agrees and adds two findings**: (1) cross-harness plugin packaging is on par with superpowers — strongest concrete reference for COS cross-harness emit; (2) the 1-month-old project shows worrying metric-pump signals (51k★ + 6.7k forks in 30 days) consistent with several other repos in this batch. Verdict ADOPT confirmed for benchmarks + plugin patterns; verify community signals on substance.

### Raw Metrics Appendix
```
{"name":"mempalace","license":"MIT","stars":51257,"forks":6746,"language":"Python","pushed":"2026-05-06T06:33:45Z","created":"2026-04-05T01:12:07Z","open_issues":524,"size":17113 KB}
tags: v3.3.4,v3.3.3,v3.3.2,v3.3.1,v3.3.0
issues_30d=100+, CI=9/10 success
```
