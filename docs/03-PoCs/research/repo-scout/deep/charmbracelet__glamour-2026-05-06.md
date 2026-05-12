---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/charmbracelet/glamour
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: charmbracelet/glamour

### Classification: ASSESS
**Score**: 8.1/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: tui-charm-go  •  **Surface role**: tui-component

### Summary
Stylesheet-based markdown rendering for your CLI apps 💇🏻‍♀️

**Verdict rationale**: ADR-173 SURFACE-5 sub-component (markdown rendering). Smaller surface — easier adoption proof if/when bubbletea adopted, currently blocked by upstream gate.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 6/10 | markdown rendering for terminal |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-04-27T09:56:14Z |
| Maturity | 15% | 8/10 | 3,456★ / 268 forks / 5 recent tags |
| Integration | 10% | 6/10 | tui-component |
| **Weighted Total** | | **8.1/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 115 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI red (5/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 3,456★, last push 2026-04-27T09:56:14Z
- **Default branch**: main
- **Topics**: cli, go, golang, hacktoberfest, markdown, tui
- **Notes**: 
- (none)

### ADR-187 Source-Level Proof Pack (partial — supports ASSESS verdict, not adopt)

Files cited (read directly via `gh api .../contents/<path>`):

- glamour.go (~8KB) — TermRenderer wraps blackfriday markdown AST; ANSI styling via lipgloss

**What still missing for an adoption ADR**: COS-fit matrix vs ADR-172 surfaces (lifecycle / doctrine / audit / hook / agent rendering); reversibility plan; integration boundary (read-only vs read-write into COS artifacts); 30/60/90-day falsifiable success criteria. These belong in a separate `ADR-XXX-surface-5-adopt-glamour.md` per ADR-187 §Decision.

### Integration Plan
- **What to use**: markdown rendering for terminal
- **Effort**: medium (library import)
- **Blocking**: ADR-187 source-level proof pack required before any in-process adoption

### Risks
- **License compatibility**: permissive — clean
- **Surface-5 gate** (ADR-173/187): BINDING — adoption requires separate ADR with full proof pack
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
  "created_at": "2019-12-18T23:36:15Z",
  "default_branch": "main",
  "description": "Stylesheet-based markdown rendering for your CLI apps \ud83d\udc87\ud83c\udffb\u200d\u2640\ufe0f",
  "forks": 268,
  "full_name": "charmbracelet/glamour",
  "homepage": "",
  "language": "Go",
  "license": "MIT",
  "name": "glamour",
  "open_issues": 115,
  "pushed_at": "2026-04-27T09:56:14Z",
  "stars": 3456,
  "topics": [
    "cli",
    "go",
    "golang",
    "hacktoberfest",
    "markdown",
    "tui"
  ]
}
```

</details>
