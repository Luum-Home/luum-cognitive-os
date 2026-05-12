---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/gitui-org/gitui
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: gitui-org/gitui

### Classification: REJECT
**Score**: 7.4/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
Blazing 💥 fast terminal-ui for git written in rust 🦀

**Verdict rationale**: Off-theme: Rust git TUI. No COS surface — git already covered via gh CLI + Bash.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 4/10 | git TUI; reference |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-04-23T01:39:06Z |
| Maturity | 15% | 8/10 | 21,879★ / 716 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **7.4/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 294 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (10/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 21,879★, last push 2026-04-23T01:39:06Z
- **Default branch**: master
- **Topics**: async, bash, command-line-interface, command-line-tool, git, hacktoberfest, rust, terminal, tui
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: git TUI; reference
- **Effort**: small (sub-process invocation)
- **Blocking**: none — adopt or reject directly

### Risks
- **License compatibility**: permissive — clean
- **Surface-5 gate** (ADR-173/187): not applicable
- **Theme drift**: high — off-COS-theme
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
  "created_at": "2020-03-16T14:38:01Z",
  "default_branch": "master",
  "description": "Blazing \ud83d\udca5 fast terminal-ui for git written in rust \ud83e\udd80",
  "forks": 716,
  "full_name": "gitui-org/gitui",
  "homepage": "",
  "language": "Rust",
  "license": "MIT",
  "name": "gitui",
  "open_issues": 294,
  "pushed_at": "2026-04-23T01:39:06Z",
  "stars": 21879,
  "topics": [
    "async",
    "bash",
    "command-line-interface",
    "command-line-tool",
    "git",
    "hacktoberfest",
    "rust",
    "terminal",
    "tui"
  ]
}
```

</details>
