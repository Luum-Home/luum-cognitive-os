---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/allinurl/goaccess
batch: phase2-deep-tier2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: allinurl/goaccess

### Classification: REJECT
**Score**: 7.1/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: dev-tools-tui  •  **Surface role**: tui-app

### Summary
GoAccess is a real-time web log analyzer and interactive viewer that runs in a terminal in *nix systems or through your browser.

**Verdict rationale**: Off-theme: web-server log analyzer (C). No agent/skill/memory primitive.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 3/10 | log analyzer; off-theme |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | last push 2026-04-23T22:31:12Z |
| Maturity | 15% | 8/10 | 20,512★ / 1,177 forks / 5 recent tags |
| Integration | 10% | 5/10 | tui-app |
| **Weighted Total** | | **7.1/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 443 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (10/10) |

### Key Findings
- **License**: MIT
- **Stars / activity**: 20,512★, last push 2026-04-23T22:31:12Z
- **Default branch**: master
- **Topics**: analytics, apache, c, caddy, cli, command-line, dashboard, data-analysis, gdpr, goaccess, google-analytics, monitoring, ncurses, nginx, privacy, real-time, terminal, tui, web-analytics, webserver
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: log analyzer; off-theme
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
  "created_at": "2013-07-14T03:42:08Z",
  "default_branch": "master",
  "description": "GoAccess is a real-time web log analyzer and interactive viewer that runs in a terminal in *nix systems or through your browser.",
  "forks": 1177,
  "full_name": "allinurl/goaccess",
  "homepage": "https://goaccess.io",
  "language": "C",
  "license": "MIT",
  "name": "goaccess",
  "open_issues": 443,
  "pushed_at": "2026-04-23T22:31:12Z",
  "stars": 20512,
  "topics": [
    "analytics",
    "apache",
    "c",
    "caddy",
    "cli",
    "command-line",
    "dashboard",
    "data-analysis",
    "gdpr",
    "goaccess",
    "google-analytics",
    "monitoring",
    "ncurses",
    "nginx",
    "privacy",
    "real-time",
    "terminal",
    "tui",
    "web-analytics",
    "webserver"
  ]
}
```

</details>
