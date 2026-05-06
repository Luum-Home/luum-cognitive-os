---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/OpenHands/OpenHands
batch: phase2-deep-tier2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: OpenHands/OpenHands

### Classification: MONITOR
**Score**: 8.65/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: agent-orchestration  •  **Surface role**: framework

### Summary
🙌 OpenHands: AI-Driven Development

**Verdict rationale**: Mixed license (MIT non-enterprise/, proprietary enterprise/). Already on tier-2 list per parent radar §66. ACI patterns useful but framework competes with COS architecture — pattern harvest only, no adoption.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 7/10 | harness comparison; ACI patterns |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-06T05:57:03Z |
| Maturity | 15% | 9/10 | 72,709★ / 9,200 forks / 5 recent tags |
| Integration | 10% | 7/10 | framework |
| **Weighted Total** | | **8.65/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 416 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (9/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 72,709★, last push 2026-05-06T05:57:03Z
- **Default branch**: main
- **Topics**: agent, artificial-intelligence, chatgpt, claude-ai, cli, developer-tools, gpt, llm, openai
- **Notes**: 
- Mixed: MIT for non-`enterprise/` paths; enterprise/ proprietary

### Integration Plan
- **What to use**: harness comparison; ACI patterns
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
  "created_at": "2024-03-13T03:33:31Z",
  "default_branch": "main",
  "description": "\ud83d\ude4c OpenHands: AI-Driven Development",
  "forks": 9200,
  "full_name": "OpenHands/OpenHands",
  "homepage": "https://openhands.dev",
  "language": "Python",
  "license": "NOASSERTION",
  "name": "OpenHands",
  "open_issues": 416,
  "pushed_at": "2026-05-06T05:57:03Z",
  "stars": 72709,
  "topics": [
    "agent",
    "artificial-intelligence",
    "chatgpt",
    "claude-ai",
    "cli",
    "developer-tools",
    "gpt",
    "llm",
    "openai"
  ]
}
```

</details>
