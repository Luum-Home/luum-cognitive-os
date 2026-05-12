---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/zellij-org/zellij
batch: phase2-deep-tier2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: zellij-org/zellij

### Classification: ASSESS
**Score**: 7.7/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
A terminal workspace with batteries included

**Verdict rationale**: Rust terminal multiplexer. Possible session host for agent fan-out (cf. orchestrator parallel agents). Read-only audit of pane/session model. Not Surface-5 (multiplexer, not UI substrate).

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 5/10 | terminal multiplexer; possible session host |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-05T14:07:04Z |
| Maturity | 15% | 8/10 | 32,194★ / 1,160 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **7.7/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 1674 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI flaky (8/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 32,194★, last push 2026-05-05T14:07:04Z
- **Default branch**: main
- **Topics**: multiplexer, terminal, workspace
- **Notes**: 
- (none)

### ADR-187 Source-Level Proof Pack (partial — supports ASSESS verdict, not adopt)

Files cited (read directly via `gh api .../contents/<path>`):

- src/main.rs:5–17 — clap CLI + zellij_utils::cli::CliArgs::parse(); zellij_client + zellij_server crate split (client/server IPC architecture)

**What still missing for an adoption ADR**: COS-fit matrix vs ADR-172 surfaces (lifecycle / doctrine / audit / hook / agent rendering); reversibility plan; integration boundary (read-only vs read-write into COS artifacts); 30/60/90-day falsifiable success criteria. These belong in a separate `ADR-XXX-surface-5-adopt-zellij.md` per ADR-187 §Decision.

### Integration Plan
- **What to use**: terminal multiplexer; possible session host
- **Effort**: small (sub-process invocation)
- **Blocking**: none — adopt or reject directly

### Risks
- **License compatibility**: permissive — clean
- **Surface-5 gate** (ADR-173/187): not applicable
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
  "created_at": "2020-09-01T14:04:28Z",
  "default_branch": "main",
  "description": "A terminal workspace with batteries included",
  "forks": 1160,
  "full_name": "zellij-org/zellij",
  "homepage": "https://zellij.dev",
  "language": "Rust",
  "license": "MIT",
  "name": "zellij",
  "open_issues": 1674,
  "pushed_at": "2026-05-05T14:07:04Z",
  "stars": 32194,
  "topics": [
    "multiplexer",
    "terminal",
    "workspace"
  ]
}
```

</details>
