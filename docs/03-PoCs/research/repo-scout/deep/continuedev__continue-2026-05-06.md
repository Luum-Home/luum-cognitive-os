---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/continuedev/continue
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: continuedev/continue

### Classification: MONITOR
**Score**: 8.0/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: agent-codegen  •  **Surface role**: ide-extension

### Summary
⏩ Source-controlled AI checks, enforceable in CI. Powered by the open-source Continue CLI

**Verdict rationale**: Apache-2.0 33k★ — IDE extension competing with Claude Code harness. Pattern harvest only, no adoption (different harness shape).

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 6/10 | monitor; competitor-class |
| License | 25% | 10/10 | Apache-2.0 |
| Activity | 20% | 10/10 | last push 2026-05-05T16:20:21Z |
| Maturity | 15% | 8/10 | 32,991★ / 4,460 forks / 5 recent tags |
| Integration | 10% | 5/10 | ide-extension |
| **Weighted Total** | | **8.0/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 689 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI red (3/10) |

### Key Findings
- **License**: Apache-2.0
- **Stars / activity**: 32,991★, last push 2026-05-05T16:20:21Z
- **Default branch**: main
- **Topics**: agent, ai, cli, developer-tools, jetbrains-plugin, llm, open-source, vs-code-extenstion
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: monitor; competitor-class
- **Effort**: medium
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
  "created_at": "2023-05-24T03:39:39Z",
  "default_branch": "main",
  "description": "\u23e9 Source-controlled AI checks, enforceable in CI. Powered by the open-source Continue CLI",
  "forks": 4460,
  "full_name": "continuedev/continue",
  "homepage": "https://docs.continue.dev",
  "language": "TypeScript",
  "license": "Apache-2.0",
  "name": "continue",
  "open_issues": 689,
  "pushed_at": "2026-05-05T16:20:21Z",
  "stars": 32991,
  "topics": [
    "agent",
    "ai",
    "cli",
    "developer-tools",
    "jetbrains-plugin",
    "llm",
    "open-source",
    "vs-code-extenstion"
  ]
}
```

</details>
