---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/charmbracelet/gum
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: charmbracelet/gum

### Classification: ASSESS
**Score**: 8.5/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: tui-charm-go  •  **Surface role**: tui-cli

### Summary
A tool for glamorous shell scripts 🎀

**Verdict rationale**: Shell-script TUI primitive (Go binary). Lower SURFACE-5 risk than bubbletea (CLI sub-process not in-process substrate). Possible candidate for hooks/skills shell glue. Source-level proof still required if invoked from COS shell paths.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 7/10 | shell-script TUI primitives; pairs with hooks |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-04T14:06:08Z |
| Maturity | 15% | 8/10 | 23,551★ / 497 forks / 5 recent tags |
| Integration | 10% | 7/10 | tui-cli |
| **Weighted Total** | | **8.5/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 160 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI flaky (7/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 23,551★, last push 2026-05-04T14:06:08Z
- **Default branch**: main
- **Topics**: bash, shell
- **Notes**: 
- (none)

### ADR-187 Source-Level Proof Pack (partial — supports ASSESS verdict, not adopt)

Files cited (read directly via `gh api .../contents/<path>`):

- main.go (~2KB) — kong CLI dispatcher per sub-command; each sub-command is its own bubbletea Program (process-per-invocation, not in-process integration)

**What still missing for an adoption ADR**: COS-fit matrix vs ADR-172 surfaces (lifecycle / doctrine / audit / hook / agent rendering); reversibility plan; integration boundary (read-only vs read-write into COS artifacts); 30/60/90-day falsifiable success criteria. These belong in a separate `ADR-XXX-surface-5-adopt-gum.md` per ADR-187 §Decision.

### Integration Plan
- **What to use**: shell-script TUI primitives; pairs with hooks
- **Effort**: small (sub-process invocation)
- **Blocking**: none — adopt or reject directly

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
  "created_at": "2022-06-10T22:09:42Z",
  "default_branch": "main",
  "description": "A tool for glamorous shell scripts \ud83c\udf80",
  "forks": 497,
  "full_name": "charmbracelet/gum",
  "homepage": "",
  "language": "Go",
  "license": "MIT",
  "name": "gum",
  "open_issues": 160,
  "pushed_at": "2026-05-04T14:06:08Z",
  "stars": 23551,
  "topics": [
    "bash",
    "shell"
  ]
}
```

</details>
