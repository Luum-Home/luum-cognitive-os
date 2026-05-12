---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/yorukot/superfile
batch: phase2-deep-tier2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: yorukot/superfile

### Classification: REJECT
**Score**: 7.1/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
Pretty fancy and modern terminal file manager

**Verdict rationale**: Off-theme: file manager (Go bubbletea). Reference for bubbletea ecosystem only.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 3/10 | file manager; off-theme |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-05T10:02:54Z |
| Maturity | 15% | 8/10 | 17,279★ / 451 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **7.1/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 184 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (9/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 17,279★, last push 2026-05-05T10:02:54Z
- **Default branch**: main
- **Topics**: bubbletea, cli, file-manager, filemanager, filesystem, golang, hacktoberfest, linux-app, terminal-app, terminal-based, tui
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: file manager; off-theme
- **Effort**: small (sub-process invocation)
- **Blocking**: none — adopt or reject directly

### Risks
- **License compatibility**: permissive — clean
- **Surface-5 gate** (ADR-173/187): not applicable
- **Theme drift**: high — off-COS-theme
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
  "created_at": "2024-03-19T15:49:52Z",
  "default_branch": "main",
  "description": "Pretty fancy and modern terminal file manager",
  "forks": 451,
  "full_name": "yorukot/superfile",
  "homepage": "https://superfile.dev",
  "language": "Go",
  "license": "MIT",
  "name": "superfile",
  "open_issues": 184,
  "pushed_at": "2026-05-05T10:02:54Z",
  "stars": 17279,
  "topics": [
    "bubbletea",
    "cli",
    "file-manager",
    "filemanager",
    "filesystem",
    "golang",
    "hacktoberfest",
    "linux-app",
    "terminal-app",
    "terminal-based",
    "tui"
  ]
}
```

</details>
