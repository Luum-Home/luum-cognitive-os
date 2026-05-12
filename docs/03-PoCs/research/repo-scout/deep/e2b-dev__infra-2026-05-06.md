---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/e2b-dev/infra
batch: phase2-deep-tier2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: e2b-dev/infra

### Classification: MONITOR
**Score**: 8.1/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: security-supply  •  **Surface role**: infra

### Summary
Infrastructure that's powering E2B Cloud.

**Verdict rationale**: E2B sandbox infrastructure (Go). Apache-2.0. Companion to existing [e2b-integration] skill. Not a primitive to adopt — track upstream releases.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 6/10 | E2B sandbox infra; companion to e2b skill |
| License | 25% | 10/10 | Apache-2.0 |
| Activity | 20% | 10/10 | last push 2026-05-06T06:30:57Z |
| Maturity | 15% | 8/10 | 1,081★ / 295 forks / 5 recent tags |
| Integration | 10% | 6/10 | infra |
| **Weighted Total** | | **8.1/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 69 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (9/9) |

### Key Findings
- **License**: Apache-2.0
- **Stars / activity**: 1,081★, last push 2026-05-06T06:30:57Z
- **Default branch**: main
- **Topics**: ai-agents, code-interpreter, consul, devtools, firecracker, gcp, go, golang, gpt, kvm, llm, microvm, nomad, sandbox, terraform, vm, vmm
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: E2B sandbox infra; companion to e2b skill
- **Effort**: medium
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
  "created_at": "2023-08-10T17:37:55Z",
  "default_branch": "main",
  "description": "Infrastructure that's powering E2B Cloud.",
  "forks": 295,
  "full_name": "e2b-dev/infra",
  "homepage": "https://e2b.dev",
  "language": "Go",
  "license": "Apache-2.0",
  "name": "infra",
  "open_issues": 69,
  "pushed_at": "2026-05-06T06:30:57Z",
  "stars": 1081,
  "topics": [
    "ai-agents",
    "code-interpreter",
    "consul",
    "devtools",
    "firecracker",
    "gcp",
    "go",
    "golang",
    "gpt",
    "kvm",
    "llm",
    "microvm",
    "nomad",
    "sandbox",
    "terraform",
    "vm",
    "vmm"
  ]
}
```

</details>
