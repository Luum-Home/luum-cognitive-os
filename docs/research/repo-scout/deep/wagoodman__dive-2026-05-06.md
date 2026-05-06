---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/wagoodman/dive
batch: phase2-deep-tier2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: wagoodman/dive

### Classification: REJECT
**Score**: 7.05/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
A tool for exploring each layer in a docker image

**Verdict rationale**: Off-theme: Docker layer explorer (Go). Off-theme; STALE last push 2025-12-15 — borderline activity.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 5/10 | docker layer explorer; ops |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 6/10 | last push 2025-12-15T17:20:36Z |
| Maturity | 15% | 9/10 | 53,874★ / 1,992 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **7.05/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 203 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (9/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 53,874★, last push 2025-12-15T17:20:36Z
- **Default branch**: main
- **Topics**: cli, docker, docker-image, explorer, inspector, tui
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: docker layer explorer; ops
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
  "created_at": "2018-05-13T15:44:01Z",
  "default_branch": "main",
  "description": "A tool for exploring each layer in a docker image",
  "forks": 1992,
  "full_name": "wagoodman/dive",
  "homepage": "",
  "language": "Go",
  "license": "MIT",
  "name": "dive",
  "open_issues": 203,
  "pushed_at": "2025-12-15T17:20:36Z",
  "stars": 53874,
  "topics": [
    "cli",
    "docker",
    "docker-image",
    "explorer",
    "inspector",
    "tui"
  ]
}
```

</details>
