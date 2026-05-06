---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/charmbracelet/bubbletea
batch: phase2-deep-tier2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: charmbracelet/bubbletea

### Classification: ASSESS
**Score**: 8.8/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: tui-charm-go  •  **Surface role**: tui-substrate

### Summary
A powerful little TUI framework 🏗

**Verdict rationale**: ADR-173 SURFACE-5 framework (Go). 42k★ MIT. SOURCE-LEVEL PROOF GATE PENDING per ADR-187 — require cited proof of Model/Update/View boundary, message routing, and provider/tool boundary fit against ADR-172. Lifted from tier-2 to read-only deep audit; not adopt.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 8/10 | Surface-5 framework (Go) — top candidate |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-04-24T23:27:04Z |
| Maturity | 15% | 8/10 | 42,116★ / 1,201 forks / 5 recent tags |
| Integration | 10% | 7/10 | tui-substrate |
| **Weighted Total** | | **8.8/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 173 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI flaky (7/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 42,116★, last push 2026-04-24T23:27:04Z
- **Default branch**: main
- **Topics**: cli, elm-architecture, framework, functional, go, golang, hacktoberfest, tui
- **Notes**: 
- (none)

### ADR-187 Source-Level Proof Pack (partial — supports ASSESS verdict, not adopt)

Files cited (read directly via `gh api .../contents/<path>`):

- tea.go:50 — `type Msg = uv.Event` (event type alias for ulid/uv stream)
- tea.go:53 — `type Model interface` (Init/Update/View contract — Elm Architecture core)
- tea.go:84 — `type View struct` (immutable view artifact)
- tea.go:390 — `type Cmd func() Msg` (effects-as-functions, deferred-execution)
- tea.go:426 — `type Program struct` (runtime: input loop + signal handling + alt-screen)

**What still missing for an adoption ADR**: COS-fit matrix vs ADR-172 surfaces (lifecycle / doctrine / audit / hook / agent rendering); reversibility plan; integration boundary (read-only vs read-write into COS artifacts); 30/60/90-day falsifiable success criteria. These belong in a separate `ADR-XXX-surface-5-adopt-bubbletea.md` per ADR-187 §Decision.

### Integration Plan
- **What to use**: Surface-5 framework (Go) — top candidate
- **Effort**: large (substrate-level)
- **Blocking**: ADR-187 source-level proof pack required before any in-process adoption

### Risks
- **License compatibility**: permissive — clean
- **Surface-5 gate** (ADR-173/187): BINDING — adoption requires separate ADR with full proof pack
- **Theme drift**: low
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
  "created_at": "2020-01-10T21:04:03Z",
  "default_branch": "main",
  "description": "A powerful little TUI framework \ud83c\udfd7",
  "forks": 1201,
  "full_name": "charmbracelet/bubbletea",
  "homepage": "",
  "language": "Go",
  "license": "MIT",
  "name": "bubbletea",
  "open_issues": 173,
  "pushed_at": "2026-04-24T23:27:04Z",
  "stars": 42116,
  "topics": [
    "cli",
    "elm-architecture",
    "framework",
    "functional",
    "go",
    "golang",
    "hacktoberfest",
    "tui"
  ]
}
```

</details>
