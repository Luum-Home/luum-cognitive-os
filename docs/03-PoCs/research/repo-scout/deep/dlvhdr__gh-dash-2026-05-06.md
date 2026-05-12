---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/dlvhdr/gh-dash
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: dlvhdr/gh-dash

### Classification: ASSESS
**Score**: 7.7/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
A rich terminal UI for GitHub that doesn't break your flow.

**Verdict rationale**: GitHub PR/issue dashboard (Go bubbletea app). Reference TUI architecture pattern — read-only proof of bubbletea-on-real-data. Same SURFACE-5 gate as bubbletea for adoption.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 5/10 | GH dashboard; reference TUI patterns |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-05T10:53:54Z |
| Maturity | 15% | 8/10 | 11,561★ / 383 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **7.7/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 87 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI red (4/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 11,561★, last push 2026-05-05T10:53:54Z
- **Default branch**: main
- **Topics**: bubbles, bubbletea, cli, cobra, gh-extension, github, glamour, go, golang, lipgloss, terminal, tui
- **Notes**: 
- (none)

### ADR-187 Source-Level Proof Pack (partial — supports ASSESS verdict, not adopt)

Files cited (read directly via `gh api .../contents/<path>`):

- gh-dash.go — 8-line shim: `package main; cmd.Execute()`
- cmd/root.go:18–25 — Direct dependency on charm.land/bubbletea/v2 + charm.land/lipgloss/v2 + bubblezone (mouse-zone routing)
- cmd/root.go — fang (cobra wrapper) + spf13/cobra for CLI surface; tui package isolates UI logic

**What still missing for an adoption ADR**: COS-fit matrix vs ADR-172 surfaces (lifecycle / doctrine / audit / hook / agent rendering); reversibility plan; integration boundary (read-only vs read-write into COS artifacts); 30/60/90-day falsifiable success criteria. These belong in a separate `ADR-XXX-surface-5-adopt-gh-dash.md` per ADR-187 §Decision.

### Integration Plan
- **What to use**: GH dashboard; reference TUI patterns
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
  "created_at": "2021-10-14T17:53:33Z",
  "default_branch": "main",
  "description": "A rich terminal UI for GitHub that doesn't break your flow.",
  "forks": 383,
  "full_name": "dlvhdr/gh-dash",
  "homepage": "https://gh-dash.dev",
  "language": "Go",
  "license": "MIT",
  "name": "gh-dash",
  "open_issues": 87,
  "pushed_at": "2026-05-05T10:53:54Z",
  "stars": 11561,
  "topics": [
    "bubbles",
    "bubbletea",
    "cli",
    "cobra",
    "gh-extension",
    "github",
    "glamour",
    "go",
    "golang",
    "lipgloss",
    "terminal",
    "tui"
  ]
}
```

</details>
