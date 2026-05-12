---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/charmbracelet/bubbles
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: charmbracelet/bubbles

### Classification: ASSESS
**Score**: 8.5/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: tui-charm-go  •  **Surface role**: tui-substrate

### Summary
TUI components for Bubble Tea 🫧

**Verdict rationale**: ADR-173 SURFACE-5 component lib (Go) on bubbletea. Adoption requires ADR-187 proof — cite component/list/textinput modules. Same gate as bubbletea.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 7/10 | Surface-5 component lib (Go) |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-04-26T00:24:44Z |
| Maturity | 15% | 8/10 | 8,310★ / 399 forks / 5 recent tags |
| Integration | 10% | 7/10 | tui-substrate |
| **Weighted Total** | | **8.5/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 198 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI red (4/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 8,310★, last push 2026-04-26T00:24:44Z
- **Default branch**: main
- **Topics**: cli, elm-architecture, hacktoberfest, terminal, tui
- **Notes**: 
- (none)

### ADR-187 Source-Level Proof Pack (partial — supports ASSESS verdict, not adopt)

Files cited (read directly via `gh api .../contents/<path>`):

- list/list.go (~33KB) — list.Model with delegate pattern; bubbletea Model interface conformance

**What still missing for an adoption ADR**: COS-fit matrix vs ADR-172 surfaces (lifecycle / doctrine / audit / hook / agent rendering); reversibility plan; integration boundary (read-only vs read-write into COS artifacts); 30/60/90-day falsifiable success criteria. These belong in a separate `ADR-XXX-surface-5-adopt-bubbles.md` per ADR-187 §Decision.

### Integration Plan
- **What to use**: Surface-5 component lib (Go)
- **Effort**: large (substrate-level)
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
  "created_at": "2020-01-18T15:43:23Z",
  "default_branch": "main",
  "description": "TUI components for Bubble Tea \ud83e\udee7",
  "forks": 399,
  "full_name": "charmbracelet/bubbles",
  "homepage": "",
  "language": "Go",
  "license": "MIT",
  "name": "bubbles",
  "open_issues": 198,
  "pushed_at": "2026-04-26T00:24:44Z",
  "stars": 8310,
  "topics": [
    "cli",
    "elm-architecture",
    "hacktoberfest",
    "terminal",
    "tui"
  ]
}
```

</details>
