---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/jesseduffield/lazygit
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: jesseduffield/lazygit

### Classification: ASSESS
**Score**: 8.15/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
simple terminal UI for git commands

**Verdict rationale**: Reference Go TUI architecture. Listed in parent-radar §3.dev-tools-tui top-3 picks. Read-only architecture audit (UI-state-machine, dispatch, plugin model). Adoption blocked — git already via gh CLI.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 6/10 | git TUI; reference design |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-06T00:05:24Z |
| Maturity | 15% | 9/10 | 77,479★ / 2,811 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **8.15/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 957 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI flaky (8/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 77,479★, last push 2026-05-06T00:05:24Z
- **Default branch**: master
- **Topics**: cli, git, terminal
- **Notes**: 
- (none)

### ADR-187 Source-Level Proof Pack (partial — supports ASSESS verdict, not adopt)

Files cited (read directly via `gh api .../contents/<path>`):

- main.go (~423B) — package main wraps `app.Run()`; entrypoint is internal/app

**What still missing for an adoption ADR**: COS-fit matrix vs ADR-172 surfaces (lifecycle / doctrine / audit / hook / agent rendering); reversibility plan; integration boundary (read-only vs read-write into COS artifacts); 30/60/90-day falsifiable success criteria. These belong in a separate `ADR-XXX-surface-5-adopt-lazygit.md` per ADR-187 §Decision.

### Integration Plan
- **What to use**: git TUI; reference design
- **Effort**: small (sub-process invocation)
- **Blocking**: none — adopt or reject directly

### Risks
- **License compatibility**: permissive — clean
- **Surface-5 gate** (ADR-173/187): not applicable
- **Theme drift**: low
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
  "created_at": "2018-05-19T00:53:06Z",
  "default_branch": "master",
  "description": "simple terminal UI for git commands",
  "forks": 2811,
  "full_name": "jesseduffield/lazygit",
  "homepage": "",
  "language": "Go",
  "license": "MIT",
  "name": "lazygit",
  "open_issues": 957,
  "pushed_at": "2026-05-06T00:05:24Z",
  "stars": 77479,
  "topics": [
    "cli",
    "git",
    "terminal"
  ]
}
```

</details>
