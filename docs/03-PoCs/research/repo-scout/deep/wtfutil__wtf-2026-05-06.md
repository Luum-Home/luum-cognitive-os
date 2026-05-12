---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/wtfutil/wtf
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: wtfutil/wtf

### Classification: ASSESS
**Score**: 6.95/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
The personal information dashboard for your terminal

**Verdict rationale**: MPL-2.0 dashboard TUI (Go). Architecturally interesting as composable widget/module dashboard — closest analog to a Surface-5 dashboard layout. Read-only architecture audit.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 5/10 | dashboard; potential Surface-5 reference |
| License | 25% | 7/10 | MPL-2.0 |
| Activity | 20% | 10/10 | last push 2026-05-01T02:52:02Z |
| Maturity | 15% | 8/10 | 16,886★ / 846 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **6.95/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 68 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (9/10) |

### Key Findings
- **License**: MPL-2.0 — MPL-2.0: file-level copyleft, fine for sub-process invocation
- **Stars / activity**: 16,886★, last push 2026-05-01T02:52:02Z
- **Default branch**: trunk
- **Topics**: cui, dashboard, devops, go, golang, hacktoberfest, terminal, tui, wtf, wtfutil
- **Notes**: 
- (none)

### ADR-187 Source-Level Proof Pack (partial — supports ASSESS verdict, not adopt)

Files cited (read directly via `gh api .../contents/<path>`):

- main.go (~1.6KB) — go-flags CLI parser → cfg.LoadConfig → App.Run; widget-grid composable via YAML config

**What still missing for an adoption ADR**: COS-fit matrix vs ADR-172 surfaces (lifecycle / doctrine / audit / hook / agent rendering); reversibility plan; integration boundary (read-only vs read-write into COS artifacts); 30/60/90-day falsifiable success criteria. These belong in a separate `ADR-XXX-surface-5-adopt-wtf.md` per ADR-187 §Decision.

### Integration Plan
- **What to use**: dashboard; potential Surface-5 reference
- **Effort**: small (sub-process invocation)
- **Blocking**: none — adopt or reject directly

### Risks
- **License compatibility**: MPL-2.0 — file-level copyleft; OK for separate-process integration
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
  "created_at": "2018-03-29T02:42:12Z",
  "default_branch": "trunk",
  "description": "The personal information dashboard for your terminal",
  "forks": 846,
  "full_name": "wtfutil/wtf",
  "homepage": "http://wtfutil.com",
  "language": "Go",
  "license": "MPL-2.0",
  "name": "wtf",
  "open_issues": 68,
  "pushed_at": "2026-05-01T02:52:02Z",
  "stars": 16886,
  "topics": [
    "cui",
    "dashboard",
    "devops",
    "go",
    "golang",
    "hacktoberfest",
    "terminal",
    "tui",
    "wtf",
    "wtfutil"
  ]
}
```

</details>
