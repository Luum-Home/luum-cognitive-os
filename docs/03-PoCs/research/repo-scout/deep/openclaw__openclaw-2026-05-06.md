---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/openclaw/openclaw
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: openclaw/openclaw

### Classification: HOLD
**Score**: 7.55/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: cli-claw-derivatives  •  **Surface role**: wrapper

### Summary
Your own personal AI assistant. Any OS. Any Platform. The lobster way. 🦞 

**Verdict rationale**: STAR-INFLATION FLAG: 368k★ on a Claude-derivative wrapper is statistically off (largest repos on GitHub are ~300k). Same anomaly category as safishamsi/graphify in radar §5. License (MIT) and activity (active) both check out — but treat star count as suspect; re-verify via GHTorrent or trending data before any adoption signal.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 4/10 | MONITOR — verify star inflation; possible squat |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-05-06T06:35:48Z |
| Maturity | 15% | 9/10 | 368,785★ / 76,007 forks / 5 recent tags |
| Integration | 10% | 5/10 | wrapper |
| **Weighted Total** | | **7.55/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 7165 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI red (5/8) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 368,785★, last push 2026-05-06T06:35:48Z
- **Default branch**: main
- **Topics**: ai, assistant, crustacean, molty, openclaw, own-your-data, personal
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: MONITOR — verify star inflation; possible squat
- **Effort**: medium
- **Blocking**: none — adopt or reject directly

### Risks
- **License compatibility**: permissive — clean
- **Surface-5 gate** (ADR-173/187): not applicable
- **Theme drift**: low
- **Star-inflation flag**: YES — see rationale

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
  "created_at": "2025-11-24T10:16:47Z",
  "default_branch": "main",
  "description": "Your own personal AI assistant. Any OS. Any Platform. The lobster way. \ud83e\udd9e ",
  "forks": 76007,
  "full_name": "openclaw/openclaw",
  "homepage": "https://openclaw.ai",
  "language": "TypeScript",
  "license": "MIT",
  "name": "openclaw",
  "open_issues": 7165,
  "pushed_at": "2026-05-06T06:35:48Z",
  "stars": 368785,
  "topics": [
    "ai",
    "assistant",
    "crustacean",
    "molty",
    "openclaw",
    "own-your-data",
    "personal"
  ]
}
```

</details>
