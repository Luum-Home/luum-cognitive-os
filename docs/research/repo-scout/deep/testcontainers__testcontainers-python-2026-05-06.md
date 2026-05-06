---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/testcontainers/testcontainers-python
batch: phase2-deep-tier2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: testcontainers/testcontainers-python

### Classification: TRIAL
**Score**: 8.2/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: observability-eval  •  **Surface role**: library

### Summary
Testcontainers is a Python library that providing a friendly API to run Docker container. It is designed to create runtime environment to use during your automatic tests.

**Verdict rationale**: Apache-2.0 Python lib. Useful for integration test infra (sandbox patterns). Pairs with existing [e2b-integration] / could feed [persistent-agent] / cos-test compose. Adopt as conditional dev-time dep, not runtime.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 6/10 | test infra primitive |
| License | 25% | 10/10 | Apache-2.0 |
| Activity | 20% | 10/10 | last push 2026-04-30T00:47:24Z |
| Maturity | 15% | 8/10 | 2,208★ / 373 forks / 5 recent tags |
| Integration | 10% | 7/10 | library |
| **Weighted Total** | | **8.2/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 171 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI red (0/10) |

### Key Findings
- **License**: Apache-2.0
- **Stars / activity**: 2,208★, last push 2026-04-30T00:47:24Z
- **Default branch**: main
- **Topics**: database, python, python3, selenium, testcontainers, testing
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: test infra primitive
- **Effort**: medium (library import)
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
  "created_at": "2017-03-22T08:22:35Z",
  "default_branch": "main",
  "description": "Testcontainers is a Python library that providing a friendly API to run Docker container. It is designed to create runtime environment to use during your automatic tests.",
  "forks": 373,
  "full_name": "testcontainers/testcontainers-python",
  "homepage": "https://testcontainers-python.readthedocs.io/en/latest/",
  "language": "Python",
  "license": "Apache-2.0",
  "name": "testcontainers-python",
  "open_issues": 171,
  "pushed_at": "2026-04-30T00:47:24Z",
  "stars": 2208,
  "topics": [
    "database",
    "python",
    "python3",
    "selenium",
    "testcontainers",
    "testing"
  ]
}
```

</details>
