---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/sxyazi/yazi
batch: phase2-deep-tier2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: sxyazi/yazi

### Classification: REJECT
**Score**: 7.4/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
💥 Blazing fast terminal file manager written in Rust, based on async I/O.

**Verdict rationale**: Off-theme: async file manager (Rust). No COS surface.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 4/10 | file manager; off-theme |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-05T18:22:20Z |
| Maturity | 15% | 8/10 | 37,632★ / 846 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **7.4/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 64 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (10/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 37,632★, last push 2026-05-05T18:22:20Z
- **Default branch**: main
- **Topics**: android, asyncio, cli, command-line, concurrency, cross-platform, developer-tools, file-explorer, file-manager, filesystem, linux, macos, neovim, productivity, rust, terminal, tui, vim, windows
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
  "created_at": "2023-07-08T11:45:55Z",
  "default_branch": "main",
  "description": "\ud83d\udca5 Blazing fast terminal file manager written in Rust, based on async I/O.",
  "forks": 846,
  "full_name": "sxyazi/yazi",
  "homepage": "https://yazi-rs.github.io",
  "language": "Rust",
  "license": "MIT",
  "name": "yazi",
  "open_issues": 64,
  "pushed_at": "2026-05-05T18:22:20Z",
  "stars": 37632,
  "topics": [
    "android",
    "asyncio",
    "cli",
    "command-line",
    "concurrency",
    "cross-platform",
    "developer-tools",
    "file-explorer",
    "file-manager",
    "filesystem",
    "linux",
    "macos",
    "neovim",
    "productivity",
    "rust",
    "terminal",
    "tui",
    "vim",
    "windows"
  ]
}
```

</details>
