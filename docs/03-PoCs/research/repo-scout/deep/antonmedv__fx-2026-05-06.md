---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/antonmedv/fx
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: antonmedv/fx

### Classification: TRIAL
**Score**: 7.3/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
Terminal JSON viewer & processor

**Verdict rationale**: Terminal JSON viewer/processor (Go). Useful as agent-output piping primitive — pairs with agent JSONL streams. Small drop-in CLI, no framework cost.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 5/10 | JSON viewer/CLI; useful for agent output piping |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 8/10 | last push 2026-03-28T13:22:52Z |
| Maturity | 15% | 8/10 | 20,447★ / 479 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **7.3/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 20 | moderate issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (10/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 20,447★, last push 2026-03-28T13:22:52Z
- **Default branch**: master
- **Topics**: cli, command-line, json, tui
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: JSON viewer/CLI; useful for agent output piping
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
  "created_at": "2018-01-25T17:29:43Z",
  "default_branch": "master",
  "description": "Terminal JSON viewer & processor",
  "forks": 479,
  "full_name": "antonmedv/fx",
  "homepage": "https://fx.wtf",
  "language": "Go",
  "license": "MIT",
  "name": "fx",
  "open_issues": 20,
  "pushed_at": "2026-03-28T13:22:52Z",
  "stars": 20447,
  "topics": [
    "cli",
    "command-line",
    "json",
    "tui"
  ]
}
```

</details>
