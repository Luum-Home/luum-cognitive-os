---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/JackChen-me/open-multi-agent
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: JackChen-me/open-multi-agent

### Classification: ASSESS
**Score**: 8.2/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: agent-orchestration  •  **Surface role**: framework

### Summary
From a goal to a task DAG, automatically. TypeScript-native multi-agent orchestration with MCP and live tracing. Three runtime dependencies.

**Verdict rationale**: TS-native goal-to-DAG planner. Possible Engram/coordination-status alignment. Read planner pattern only; framework adoption blocked by COS-already-has-SDD.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 6/10 | harvest TS DAG planner |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-05T09:22:32Z |
| Maturity | 15% | 8/10 | 6,052★ / 2,345 forks / 5 recent tags |
| Integration | 10% | 7/10 | framework |
| **Weighted Total** | | **8.2/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 10 | moderate issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (9/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 6,052★, last push 2026-05-05T09:22:32Z
- **Default branch**: main
- **Topics**: agent-framework, ai-agents, anthropic, claude, deepseek, gemini, grok, llm, local-llm, mcp, model-agnostic, multi-agent, nodejs, ollama, openai, orchestration, structured-output, task-scheduling, tool-use, typescript
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: harvest TS DAG planner
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
  "created_at": "2026-03-31T19:07:34Z",
  "default_branch": "main",
  "description": "From a goal to a task DAG, automatically. TypeScript-native multi-agent orchestration with MCP and live tracing. Three runtime dependencies.",
  "forks": 2345,
  "full_name": "JackChen-me/open-multi-agent",
  "homepage": "https://open-multi-agent.com",
  "language": "TypeScript",
  "license": "MIT",
  "name": "open-multi-agent",
  "open_issues": 10,
  "pushed_at": "2026-05-05T09:22:32Z",
  "stars": 6052,
  "topics": [
    "agent-framework",
    "ai-agents",
    "anthropic",
    "claude",
    "deepseek",
    "gemini",
    "grok",
    "llm",
    "local-llm",
    "mcp",
    "model-agnostic",
    "multi-agent",
    "nodejs",
    "ollama",
    "openai",
    "orchestration",
    "structured-output",
    "task-scheduling",
    "tool-use",
    "typescript"
  ]
}
```

</details>
