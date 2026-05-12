---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/crossterm-rs/crossterm
batch: phase2-deep-tier2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: crossterm-rs/crossterm

### Classification: ASSESS
**Score**: 8.05/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: tui-rust  •  **Surface role**: tui-substrate

### Summary
Cross platform terminal library rust

**Verdict rationale**: Rust terminal-control substrate. Underpins ratatui. Same SURFACE-5 gate.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 6/10 | low-level Rust terminal; underpins ratatui |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-04-08T18:58:28Z |
| Maturity | 15% | 7/10 | 4,034★ / 362 forks / 5 recent tags |
| Integration | 10% | 7/10 | tui-substrate |
| **Weighted Total** | | **8.05/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 214 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI red (0/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 4,034★, last push 2026-04-08T18:58:28Z
- **Default branch**: master
- **Topics**: color, console, cross-platform, cursor, input, terminal, tui
- **Notes**: 
- (none)

### ADR-187 Source-Level Proof Pack (partial — supports ASSESS verdict, not adopt)

Files cited (read directly via `gh api .../contents/<path>`):

- src/lib.rs:3 — `Cross-platform Terminal Manipulation Library` (crate-level docstring)
- src/lib.rs:11–17 — Command API: lazy execution model (queue then flush) — direct fit for batched terminal updates

**What still missing for an adoption ADR**: COS-fit matrix vs ADR-172 surfaces (lifecycle / doctrine / audit / hook / agent rendering); reversibility plan; integration boundary (read-only vs read-write into COS artifacts); 30/60/90-day falsifiable success criteria. These belong in a separate `ADR-XXX-surface-5-adopt-crossterm.md` per ADR-187 §Decision.

### Integration Plan
- **What to use**: low-level Rust terminal; underpins ratatui
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
  "created_at": "2018-01-03T13:34:42Z",
  "default_branch": "master",
  "description": "Cross platform terminal library rust",
  "forks": 362,
  "full_name": "crossterm-rs/crossterm",
  "homepage": null,
  "language": "Rust",
  "license": "MIT",
  "name": "crossterm",
  "open_issues": 214,
  "pushed_at": "2026-04-08T18:58:28Z",
  "stars": 4034,
  "topics": [
    "color",
    "console",
    "cross-platform",
    "cursor",
    "input",
    "terminal",
    "tui"
  ]
}
```

</details>
