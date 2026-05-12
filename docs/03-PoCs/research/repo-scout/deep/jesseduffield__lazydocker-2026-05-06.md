---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/jesseduffield/lazydocker
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: jesseduffield/lazydocker

### Classification: REJECT
**Score**: 7.85/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
The lazier way to manage everything docker

**Verdict rationale**: Off-theme: Docker TUI (Go). Reference pattern only — verdict matches dev-tools-tui cluster intent (top-3 picks were lazygit/k9s/gh-dash; lazydocker not among them).

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 5/10 | docker TUI; reference |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-04-19T02:51:06Z |
| Maturity | 15% | 9/10 | 50,918★ / 1,610 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **7.85/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 274 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI red (5/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 50,918★, last push 2026-04-19T02:51:06Z
- **Default branch**: master
- **Topics**: (none)
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: docker TUI; reference
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
  "created_at": "2019-05-18T08:53:50Z",
  "default_branch": "master",
  "description": "The lazier way to manage everything docker",
  "forks": 1610,
  "full_name": "jesseduffield/lazydocker",
  "homepage": "",
  "language": "Go",
  "license": "MIT",
  "name": "lazydocker",
  "open_issues": 274,
  "pushed_at": "2026-04-19T02:51:06Z",
  "stars": 50918,
  "topics": []
}
```

</details>
