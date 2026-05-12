---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/ratatui/ratatui
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: ratatui/ratatui

### Classification: ASSESS
**Score**: 8.5/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: tui-rust  •  **Surface role**: tui-substrate

### Summary
A Rust crate for cooking up terminal user interfaces (TUIs) 👨‍🍳🐀 https://ratatui.rs

**Verdict rationale**: ADR-173 SURFACE-5 candidate (Rust TUI substrate). MIT, 20k★. SOURCE-LEVEL PROOF GATE PENDING per ADR-187 — requires cited proof of Frame/Widget/Layout boundary against ADR-172.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 7/10 | Surface-5 candidate (Rust TUI) |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-04T21:08:27Z |
| Maturity | 15% | 8/10 | 20,215★ / 648 forks / 5 recent tags |
| Integration | 10% | 7/10 | tui-substrate |
| **Weighted Total** | | **8.5/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 193 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (9/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 20,215★, last push 2026-05-04T21:08:27Z
- **Default branch**: main
- **Topics**: cli, ratatui, rust, terminal, terminal-user-interface, tui, widgets
- **Notes**: 
- (none)

### ADR-187 Source-Level Proof Pack (partial — supports ASSESS verdict, not adopt)

Files cited (read directly via `gh api .../contents/<path>`):

- ARCHITECTURE.md:13–54 — Crate organization: ratatui (apps), ratatui-core (widget authors), ratatui-widgets, ratatui-{crossterm,termion,termwiz} backends
- ratatui-core/src/lib.rs:1 — `#![no_std]` (embedded-target compatible)
- ratatui-core/src/lib.rs:8–18 — split from main crate for API stability (widget libraries depend on -core)

**What still missing for an adoption ADR**: COS-fit matrix vs ADR-172 surfaces (lifecycle / doctrine / audit / hook / agent rendering); reversibility plan; integration boundary (read-only vs read-write into COS artifacts); 30/60/90-day falsifiable success criteria. These belong in a separate `ADR-XXX-surface-5-adopt-ratatui.md` per ADR-187 §Decision.

### Integration Plan
- **What to use**: Surface-5 candidate (Rust TUI)
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
  "created_at": "2023-02-12T21:56:20Z",
  "default_branch": "main",
  "description": "A Rust crate for cooking up terminal user interfaces (TUIs) \ud83d\udc68\u200d\ud83c\udf73\ud83d\udc00 https://ratatui.rs",
  "forks": 648,
  "full_name": "ratatui/ratatui",
  "homepage": "https://ratatui.rs",
  "language": "Rust",
  "license": "MIT",
  "name": "ratatui",
  "open_issues": 193,
  "pushed_at": "2026-05-04T21:08:27Z",
  "stars": 20215,
  "topics": [
    "cli",
    "ratatui",
    "rust",
    "terminal",
    "terminal-user-interface",
    "tui",
    "widgets"
  ]
}
```

</details>
