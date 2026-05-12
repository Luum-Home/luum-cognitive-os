---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/agentscope-ai/agentscope
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: agentscope-ai/agentscope

### Classification: MONITOR
**Score**: 8.2/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: agent-orchestration  •  **Surface role**: framework

### Summary
Build and run agents you can see, understand and trust.

**Verdict rationale**: Apache-2.0 24k★ multi-agent framework. Framework-class competitor; harvest agent-state-rendering patterns, no adoption — COS uses skill+SDD pipeline.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 6/10 | monitor; framework-fit weak |
| License | 25% | 10/10 | Apache-2.0 |
| Activity | 20% | 10/10 | last push 2026-04-30T08:27:43Z |
| Maturity | 15% | 8/10 | 24,625★ / 2,654 forks / 5 recent tags |
| Integration | 10% | 7/10 | framework |
| **Weighted Total** | | **8.2/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 219 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI red (5/10) |

### Key Findings
- **License**: Apache-2.0
- **Stars / activity**: 24,625★, last push 2026-04-30T08:27:43Z
- **Default branch**: main
- **Topics**: agent, chatbot, large-language-models, llm, llm-agent, mcp, multi-agent, multi-modal, react-agent
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: monitor; framework-fit weak
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
  "created_at": "2024-01-12T03:41:59Z",
  "default_branch": "main",
  "description": "Build and run agents you can see, understand and trust.",
  "forks": 2654,
  "full_name": "agentscope-ai/agentscope",
  "homepage": "https://docs.agentscope.io/",
  "language": "Python",
  "license": "Apache-2.0",
  "name": "agentscope",
  "open_issues": 219,
  "pushed_at": "2026-04-30T08:27:43Z",
  "stars": 24625,
  "topics": [
    "agent",
    "chatbot",
    "large-language-models",
    "llm",
    "llm-agent",
    "mcp",
    "multi-agent",
    "multi-modal",
    "react-agent"
  ]
}
```

</details>
