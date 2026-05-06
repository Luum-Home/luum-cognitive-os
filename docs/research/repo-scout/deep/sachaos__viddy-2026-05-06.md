---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/sachaos/viddy
batch: phase2-deep-tier2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: sachaos/viddy

### Classification: REJECT
**Score**: 7.0/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
👀 A modern watch command. Time machine and pager etc.

**Verdict rationale**: Off-theme: modern watch(1) replacement (Rust). No COS surface.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 4/10 | watch replacement; off-theme |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 8/10 | last push 2026-02-05T18:28:09Z |
| Maturity | 15% | 8/10 | 5,325★ / 97 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **7.0/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 31 | moderate issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI red (5/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 5,325★, last push 2026-02-05T18:28:09Z
- **Default branch**: master
- **Topics**: cli, golang, terminal, tui, watch
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: watch replacement; off-theme
- **Effort**: small (sub-process invocation)
- **Blocking**: none — adopt or reject directly

### Risks
- **License compatibility**: permissive — clean
- **Surface-5 gate** (ADR-173/187): not applicable
- **Theme drift**: high — off-COS-theme
- **Star-inflation flag**: no

### Cross-References
- Parent radar: `docs/reports/external-tools-radar-2026-05-06.md`
- Sister batch (tier-1 top-22): wrote to `docs/research/repo-scout/deep/`
- ADR-173 (research gate): `docs/adrs/ADR-173-surface-5-research-gate.md`
- ADR-187 (proof contract): `docs/adrs/ADR-187-surface-5-adoption-proof-contract.md`

### Raw Metrics
<details>
<summary>gh api JSON (key fields)</summary>

```json
{
  "archived": false,
  "created_at": "2021-08-14T06:40:12Z",
  "default_branch": "master",
  "description": "\ud83d\udc40 A modern watch command. Time machine and pager etc.",
  "forks": 97,
  "full_name": "sachaos/viddy",
  "homepage": "",
  "language": "Rust",
  "license": "MIT",
  "name": "viddy",
  "open_issues": 31,
  "pushed_at": "2026-02-05T18:28:09Z",
  "stars": 5325,
  "topics": [
    "cli",
    "golang",
    "terminal",
    "tui",
    "watch"
  ]
}
```

</details>
