---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/ComposioHQ/agent-orchestrator
batch: phase2-deep-tier2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: ComposioHQ/agent-orchestrator

### Classification: TRIAL
**Score**: 8.5/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: agent-orchestration  •  **Surface role**: framework

### Summary
 Agentic orchestrator for parallel coding agents — plans tasks, spawns agents, and autonomously handles CI    fixes, merge conflicts, and code reviews.

**Verdict rationale**: Genuine planner DAG primitive (TS); MONITOR for harness comparison, not adopt — COS already has SDD pipeline (ADR-027) covering same ground. Score inflation: stars/license/activity all max but theme overlaps existing COS primitive.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 7/10 | harvest planner DAG patterns |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-06T06:29:30Z |
| Maturity | 15% | 8/10 | 6,824★ / 919 forks / 5 recent tags |
| Integration | 10% | 7/10 | framework |
| **Weighted Total** | | **8.5/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 757 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (9/9) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 6,824★, last push 2026-05-06T06:29:30Z
- **Default branch**: main
- **Topics**: agent-fleet, agent-swarm, claude-code, codex-cli, git-worktrees, multi-agent, orchestration, orchestrator, parallel-agents, parallel-coding, skills, tmux
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: harvest planner DAG patterns
- **Effort**: medium
- **Blocking**: COS architecture commitment (skill+SDD pipeline)

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
  "created_at": "2026-02-13T09:52:36Z",
  "default_branch": "main",
  "description": " Agentic orchestrator for parallel coding agents \u2014 plans tasks, spawns agents, and autonomously handles CI    fixes, merge conflicts, and code reviews.",
  "forks": 919,
  "full_name": "ComposioHQ/agent-orchestrator",
  "homepage": "https://composio.dev",
  "language": "TypeScript",
  "license": "MIT",
  "name": "agent-orchestrator",
  "open_issues": 757,
  "pushed_at": "2026-05-06T06:29:30Z",
  "stars": 6824,
  "topics": [
    "agent-fleet",
    "agent-swarm",
    "claude-code",
    "codex-cli",
    "git-worktrees",
    "multi-agent",
    "orchestration",
    "orchestrator",
    "parallel-agents",
    "parallel-coding",
    "skills",
    "tmux"
  ]
}
```

</details>
