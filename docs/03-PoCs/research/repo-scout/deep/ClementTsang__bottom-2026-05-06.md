---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/ClementTsang/bottom
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: ClementTsang/bottom

### Classification: REJECT
**Score**: 7.4/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
Yet another cross-platform graphical process/system monitor.

**Verdict rationale**: Off-theme: cross-platform process/system monitor; not a COS surface or primitive. No agent/skill/memory delta.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 4/10 | monitor (resource viewer; not COS surface) |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-06T05:50:04Z |
| Maturity | 15% | 8/10 | 13,281★ / 336 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **7.4/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 111 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (9/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 13,281★, last push 2026-05-06T05:50:04Z
- **Default branch**: main
- **Topics**: bottom, btm, cli, cross-platform, monitoring, rust, terminal, top, tui
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: monitor (resource viewer; not COS surface)
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
  "created_at": "2019-08-28T23:43:30Z",
  "default_branch": "main",
  "description": "Yet another cross-platform graphical process/system monitor.",
  "forks": 336,
  "full_name": "ClementTsang/bottom",
  "homepage": "https://bottom.pages.dev",
  "language": "Rust",
  "license": "MIT",
  "name": "bottom",
  "open_issues": 111,
  "pushed_at": "2026-05-06T05:50:04Z",
  "stars": 13281,
  "topics": [
    "bottom",
    "btm",
    "cli",
    "cross-platform",
    "monitoring",
    "rust",
    "terminal",
    "top",
    "tui"
  ]
}
```

</details>
