---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/charmbracelet/huh
batch: phase2-deep-tier2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: charmbracelet/huh

### Classification: ASSESS
**Score**: 8.5/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: tui-charm-go  •  **Surface role**: tui-substrate

### Summary
Build terminal forms and prompts 🤷🏻‍♀️

**Verdict rationale**: Form/prompt component on bubbletea — same gate. Useful pattern source for prompt-clarification UI.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 7/10 | form/prompt component on bubbletea |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-04-22T14:14:27Z |
| Maturity | 15% | 8/10 | 6,846★ / 240 forks / 5 recent tags |
| Integration | 10% | 7/10 | tui-substrate |
| **Weighted Total** | | **8.5/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 75 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI red (5/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 6,846★, last push 2026-04-22T14:14:27Z
- **Default branch**: main
- **Topics**: (none)
- **Notes**: 
- (none)

### ADR-187 Source-Level Proof Pack (partial — supports ASSESS verdict, not adopt)

Files cited (read directly via `gh api .../contents/<path>`):

- form.go (~17KB) — Form{} composes Group{} which composes Field; bubbletea Update/View pipeline; integrates with bubbletea v2 message router

**What still missing for an adoption ADR**: COS-fit matrix vs ADR-172 surfaces (lifecycle / doctrine / audit / hook / agent rendering); reversibility plan; integration boundary (read-only vs read-write into COS artifacts); 30/60/90-day falsifiable success criteria. These belong in a separate `ADR-XXX-surface-5-adopt-huh.md` per ADR-187 §Decision.

### Integration Plan
- **What to use**: form/prompt component on bubbletea
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
  "created_at": "2023-10-11T16:59:24Z",
  "default_branch": "main",
  "description": "Build terminal forms and prompts \ud83e\udd37\ud83c\udffb\u200d\u2640\ufe0f",
  "forks": 240,
  "full_name": "charmbracelet/huh",
  "homepage": "",
  "language": "Go",
  "license": "MIT",
  "name": "huh",
  "open_issues": 75,
  "pushed_at": "2026-04-22T14:14:27Z",
  "stars": 6846,
  "topics": []
}
```

</details>
