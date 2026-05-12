---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/tstack/lnav
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: tstack/lnav

### Classification: REJECT
**Score**: 7.4/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
Log file navigator

**Verdict rationale**: Off-theme: log-file navigator (C++). No agent/skill primitive.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 4/10 | log navigator; off-theme |
| License | 25% | 10/10 | BSD-2-Clause |
| Activity | 20% | 10/10 | last push 2026-05-05T16:57:56Z |
| Maturity | 15% | 8/10 | 10,242★ / 383 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **7.4/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 269 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI flaky (8/10) |

### Key Findings
- **License**: BSD-2-Clause
- **Stars / activity**: 10,242★, last push 2026-05-05T16:57:56Z
- **Default branch**: master
- **Topics**: command-line-tool, less, log-analysis, log-monitor, log-viewer, log-visualization, logging, more, pager, tail, terminal, terminal-pager, tui
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: log navigator; off-theme
- **Effort**: small (sub-process invocation)
- **Blocking**: none — adopt or reject directly

### Risks
- **License compatibility**: permissive — clean
- **Surface-5 gate** (ADR-173/187): not applicable
- **Theme drift**: high — off-COS-theme
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
  "created_at": "2009-09-14T01:02:02Z",
  "default_branch": "master",
  "description": "Log file navigator",
  "forks": 383,
  "full_name": "tstack/lnav",
  "homepage": "http://lnav.org",
  "language": "C++",
  "license": "BSD-2-Clause",
  "name": "lnav",
  "open_issues": 269,
  "pushed_at": "2026-05-05T16:57:56Z",
  "stars": 10242,
  "topics": [
    "command-line-tool",
    "less",
    "log-analysis",
    "log-monitor",
    "log-viewer",
    "log-visualization",
    "logging",
    "more",
    "pager",
    "tail",
    "terminal",
    "terminal-pager",
    "tui"
  ]
}
```

</details>
