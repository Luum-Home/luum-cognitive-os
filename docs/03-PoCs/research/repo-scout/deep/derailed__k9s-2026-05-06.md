---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/derailed/k9s
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: derailed/k9s

### Classification: REJECT
**Score**: 7.7/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
🐶 Kubernetes CLI To Manage Your Clusters In Style!

**Verdict rationale**: Off-theme: K8s cluster admin TUI (Go). No agent/skill/memory primitive — COS uses no K8s surface.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 5/10 | K8s admin TUI; off-theme but reference architecture |
| License | 25% | 10/10 | Apache-2.0 |
| Activity | 20% | 10/10 | last push 2026-04-21T00:01:23Z |
| Maturity | 15% | 8/10 | 33,564★ / 2,160 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **7.7/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 204 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (10/10) |

### Key Findings
- **License**: Apache-2.0
- **Stars / activity**: 33,564★, last push 2026-04-21T00:01:23Z
- **Default branch**: master
- **Topics**: go, golang, k8s, k8s-cluster, k9s, kubernetes, kubernetes-cli, kubernetes-clusters
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: K8s admin TUI; off-theme but reference architecture
- **Effort**: small (sub-process invocation)
- **Blocking**: none — adopt or reject directly

### Risks
- **License compatibility**: permissive — clean
- **Surface-5 gate** (ADR-173/187): not applicable
- **Theme drift**: high — off-COS-theme
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
  "created_at": "2019-01-25T18:46:02Z",
  "default_branch": "master",
  "description": "\ud83d\udc36 Kubernetes CLI To Manage Your Clusters In Style!",
  "forks": 2160,
  "full_name": "derailed/k9s",
  "homepage": "https://k9scli.io",
  "language": "Go",
  "license": "Apache-2.0",
  "name": "k9s",
  "open_issues": 204,
  "pushed_at": "2026-04-21T00:01:23Z",
  "stars": 33564,
  "topics": [
    "go",
    "golang",
    "k8s",
    "k8s-cluster",
    "k9s",
    "kubernetes",
    "kubernetes-cli",
    "kubernetes-clusters"
  ]
}
```

</details>
