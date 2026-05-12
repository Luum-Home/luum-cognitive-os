---
evaluated_at: 2026-05-06 06:45 UTC
engram_id: pending
deepwiki_url: https://deepwiki.com/semgrep/semgrep
batch: phase2-deep-tier2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
sister_batch: phase2-deep-tier1 (top-22)
---

## Repository Evaluation: semgrep/semgrep

### Classification: TRIAL
**Score**: 7.6/10 (mechanical — qualitative override applied per radar §6 governance)
**Evaluation Level**: 2 (deep — gh API metadata + tags + workflow runs + targeted source files)
**Theme**: security-supply  •  **Surface role**: scanner

### Summary
Lightweight static analysis for many languages. Find bug variants with patterns that look like source code.

**Verdict rationale**: Static-analysis OSS engine (LGPL-2.1, OCaml). Already integrated in COS via [semgrep-scan] skill. Pattern adoption only (LGPL — link, don't statically include). Track for new rule packs (agent-aware rules).

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 7/10 | static analysis; LGPL — pattern adoption only |
| License | 25% | 6/10 | LGPL-2.1 |
| Activity | 20% | 10/10 | last push 2026-05-06T05:16:16Z |
| Maturity | 15% | 8/10 | 15,026★ / 924 forks / 5 recent tags |
| Integration | 10% | 8/10 | scanner |
| **Weighted Total** | | **7.6/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Open issues (proxy) | 870 | high issue activity |
| Release cadence | 5 recent tags | active release cadence |
| CI health | last 10 runs | CI green (10/10) |

### Key Findings
- **License**: LGPL-2.1 — LGPL: pattern adoption only, no static link
- **Stars / activity**: 15,026★, last push 2026-05-06T05:16:16Z
- **Default branch**: develop
- **Topics**: c, go, java, javascript, python, r2c, ruby, sast, semgrep, static-analysis, static-code-analysis, typescript
- **Notes**: 
- (none)

### Integration Plan
- **What to use**: static analysis; LGPL — pattern adoption only
- **Effort**: medium
- **Blocking**: none — adopt or reject directly

### Risks
- **License compatibility**: LGPL — link dynamically only; pattern-extract OK
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
  "created_at": "2019-12-13T09:29:54Z",
  "default_branch": "develop",
  "description": "Lightweight static analysis for many languages. Find bug variants with patterns that look like source code.",
  "forks": 924,
  "full_name": "semgrep/semgrep",
  "homepage": "https://semgrep.dev",
  "language": "OCaml",
  "license": "LGPL-2.1",
  "name": "semgrep",
  "open_issues": 870,
  "pushed_at": "2026-05-06T05:16:16Z",
  "stars": 15026,
  "topics": [
    "c",
    "go",
    "java",
    "javascript",
    "python",
    "r2c",
    "ruby",
    "sast",
    "semgrep",
    "static-analysis",
    "static-code-analysis",
    "typescript"
  ]
}
```

</details>
