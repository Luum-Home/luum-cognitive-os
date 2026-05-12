---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/microsoft/agent-framework
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: microsoft/agent-framework

### Classification: MONITOR
**Score**: 8.5/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: agent-orchestration  •  **Surface role**: framework

### Summary
A framework for building, orchestrating and deploying AI agents and multi-agent workflows with support for Python and .NET.

**Verdict rationale**: Apache-2.0 10k★ MSFT framework. Pattern harvest (especially MSFT semantic-kernel cross-pollination) — framework adoption blocked by COS-architecture commitment.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 7/10 | MSFT framework; harness alignment |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-06T05:02:02Z |
| Maturity | 15% | 8/10 | 10,145★ / 1,658 forks / 5 recent tags |
| Integration | 10% | 7/10 | framework |
| **Weighted Total** | | **8.5/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 815 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (10/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 10,145★, last push 2026-05-06T05:02:02Z
- **Default branch**: main
- **Topics**: agent-framework, agentic-ai, agents, ai, dotnet, multi-agent, orchestration, python, sdk, workflows
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: MSFT framework; harness alignment
- **Effort**: medium
- **Blocking**: COS architecture commitment (skill+SDD pipeline)

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
  "created_at": "2025-04-28T19:40:42Z",
  "default_branch": "main",
  "description": "A framework for building, orchestrating and deploying AI agents and multi-agent workflows with support for Python and .NET.",
  "forks": 1658,
  "full_name": "microsoft/agent-framework",
  "homepage": "https://aka.ms/agent-framework",
  "language": "Python",
  "license": "MIT",
  "name": "agent-framework",
  "open_issues": 815,
  "pushed_at": "2026-05-06T05:02:02Z",
  "stars": 10145,
  "topics": [
    "agent-framework",
    "agentic-ai",
    "agents",
    "ai",
    "dotnet",
    "multi-agent",
    "orchestration",
    "python",
    "sdk",
    "workflows"
  ]
}
```

</details>
