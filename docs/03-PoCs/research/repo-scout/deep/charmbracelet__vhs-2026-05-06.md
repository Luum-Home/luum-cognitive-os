---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/charmbracelet/vhs
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: charmbracelet/vhs

### Classification: TRIAL
**Score**: 8.0/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: tui-charm-go  •  **Surface role**: tui-app

### Summary
Your CLI home video recorder 📼

**Verdict rationale**: CLI demo recorder. Useful for skill/feature documentation GIFs. Low integration cost — invoke as sub-process. Already used elsewhere in COS docs.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 6/10 | demo recording; useful for docs |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-04T10:16:35Z |
| Maturity | 15% | 8/10 | 19,597★ / 410 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **8.0/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 150 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI red (6/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 19,597★, last push 2026-05-04T10:16:35Z
- **Default branch**: main
- **Topics**: ascii, cli, command-line, gif, recording, terminal, vhs, video
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: demo recording; useful for docs
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
  "created_at": "2022-07-19T14:28:36Z",
  "default_branch": "main",
  "description": "Your CLI home video recorder \ud83d\udcfc",
  "forks": 410,
  "full_name": "charmbracelet/vhs",
  "homepage": "",
  "language": "Go",
  "license": "MIT",
  "name": "vhs",
  "open_issues": 150,
  "pushed_at": "2026-05-04T10:16:35Z",
  "stars": 19597,
  "topics": [
    "ascii",
    "cli",
    "command-line",
    "gif",
    "recording",
    "terminal",
    "vhs",
    "video"
  ]
}
```

</details>
