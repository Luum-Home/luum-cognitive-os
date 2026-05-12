---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/charmbracelet/soft-serve
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: charmbracelet/soft-serve

### Classification: REJECT
**Score**: 7.25/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: tui-charm-go  •  **Surface role**: tui-app

### Summary
The mighty, self-hostable Git server for the command line🍦

**Verdict rationale**: Self-hosted git server. Off-theme; COS already integrates git via gh CLI.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 4/10 | self-hosted git server; off-theme |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-04T10:21:55Z |
| Maturity | 15% | 7/10 | 6,874★ / 216 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **7.25/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 89 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (10/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 6,874★, last push 2026-05-04T10:21:55Z
- **Default branch**: main
- **Topics**: git, golang, ssh
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: self-hosted git server; off-theme
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
  "created_at": "2021-07-30T23:32:44Z",
  "default_branch": "main",
  "description": "The mighty, self-hostable Git server for the command line\ud83c\udf66",
  "forks": 216,
  "full_name": "charmbracelet/soft-serve",
  "homepage": "",
  "language": "Go",
  "license": "MIT",
  "name": "soft-serve",
  "open_issues": 89,
  "pushed_at": "2026-05-04T10:21:55Z",
  "stars": 6874,
  "topics": [
    "git",
    "golang",
    "ssh"
  ]
}
```

</details>
