---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/Textualize/textual
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: Textualize/textual

### Classification: ASSESS
**Score**: 8.2/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: tui-py-other  •  **Surface role**: tui-substrate

### Summary
The lean application framework for Python.  Build sophisticated user interfaces with a simple Python API. Run your apps in the terminal and a web browser.

**Verdict rationale**: ADR-173 SURFACE-5 candidate (Python TUI substrate). MIT, 35k★, weekly releases. SOURCE-LEVEL PROOF GATE PENDING per ADR-187 — adoption requires separate ADR with cited app.py/widget/screen modules. Reading-list candidate, not adopt.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 6/10 | Surface-5 candidate (Python TUI) |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-06T05:20:14Z |
| Maturity | 15% | 8/10 | 35,739★ / 1,192 forks / 5 recent tags |
| Integration | 10% | 7/10 | tui-substrate |
| **Weighted Total** | | **8.2/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 282 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI flaky (8/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 35,739★, last push 2026-05-06T05:20:14Z
- **Default branch**: main
- **Topics**: cli, framework, python, rich, terminal, tui
- **Notes**: 
- (none)

### ADR-187 Source-Level Proof Pack (partial — supports ASSESS verdict, not adopt)

Files cited (read directly via `gh api .../contents/<path>`):

- src/textual/app.py:296 — `class App(Generic[ReturnType], DOMNode)` (root node + lifecycle)
- src/textual/app.py:560 — `def __init__` (CSS-driven layout config: classes_, watch_css, ansi_color)
- src/textual/app.py:2208 — `async def run_async` (asyncio main loop entry)
- src/textual/app.py:2121 — `async def run_test` (Pilot test harness — first-class testability)
- src/textual/app.py:4211 — `async def run_action` (action-binding dispatch)

**What still missing for an adoption ADR**: COS-fit matrix vs ADR-172 surfaces (lifecycle / doctrine / audit / hook / agent rendering); reversibility plan; integration boundary (read-only vs read-write into COS artifacts); 30/60/90-day falsifiable success criteria. These belong in a separate `ADR-XXX-surface-5-adopt-textual.md` per ADR-187 §Decision.

### Integration Plan
- **What to use**: Surface-5 candidate (Python TUI)
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
  "created_at": "2021-04-08T15:24:47Z",
  "default_branch": "main",
  "description": "The lean application framework for Python.  Build sophisticated user interfaces with a simple Python API. Run your apps in the terminal and a web browser.",
  "forks": 1192,
  "full_name": "Textualize/textual",
  "homepage": "https://textual.textualize.io/",
  "language": "Python",
  "license": "MIT",
  "name": "textual",
  "open_issues": 282,
  "pushed_at": "2026-05-06T05:20:14Z",
  "stars": 35739,
  "topics": [
    "cli",
    "framework",
    "python",
    "rich",
    "terminal",
    "tui"
  ]
}
```

</details>
