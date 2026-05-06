---
evaluated_at: 2026-05-06 06:35 UTC
evaluation_level: 2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Skill quality-validation + security-scan scoring; novel primitive; low stars)
deep_verdict: TRIAL (downgraded from ADOPT — code is real, but maintenance posture is solo + churning)
deepwiki_url: https://deepwiki.com/dmgrok/agent_skills_directory
engram_id: pending
---

## Repository Evaluation: dmgrok/agent_skills_directory

### Classification: TRIAL
**Score**: 6.6/10
**Evaluation Level**: 2 (Deep — gh api tree, schema files, CI history)

### Summary
Python CLI + JSON catalog system that aggregates skills from external sources, applies quality scoring, validates against a schema, and exports per-provider bundles (`exports/claude-skills.json`, `copilot-skills.json`, `mcp-compatible.json`). Has a homebrew formula (`homebrew-tap/Formula/skillsdir.rb`), a CI matrix (4 workflows), JSON Schema definitions (`schema/skill-manifest-schema.json`, `bundles-schema.json`, `catalog-schema.json`), and a small test suite. Novel primitive vs COS: **a curated, validated, multi-provider skill catalog with quality badges**. The `analyze_repo.py` and `validate.py` scripts are directly relevant to COS `skill-router` ranking work.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 8/10 | Quality scoring + multi-provider exports + JSON Schema for skill manifest = directly improves COS skill-router |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 9/10 | Push 2026-04-29; 5 daily-style date tags (v2026.04.25–04.29); 1 issue in 30d (very small community) |
| Maturity | 15% | 4/10 | Solo maintainer; 15 stars; daily-tag cadence indicates pre-v1 churn; CI 6/10 failing |
| Integration | 10% | 6/10 | Python CLI is easy to import; JSON exports are easy to consume; but project surface is small + shifting |
| **Weighted Total** | | **7.7/10** weighted, presented as **6.6/10** after solo-maintainer + CI-red adjustments | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 1 issue | low issue activity |
| Release cadence | 5 tags within 5 days | daily releases (high churn / pre-v1) |
| CI health | 4/10 success | CI red |

### Key Findings
- **Strengths**:
  - JSON Schema files for skill manifest, bundles, catalog (`schema/*.json`) — directly portable as a starting reference for COS skill-manifest schema.
  - Per-provider JSON exports (`claude-skills.json`, `copilot-skills.json`, `mcp-compatible.json`, `premium-skills.json`, etc.) — concrete pattern for COS `skill-registry` to emit.
  - `cli/validate.py` + `scripts/test_provider.py` + `scripts/analyze_repo.py` give a complete reference loop for skill validation + provider compatibility checks.
  - Homebrew formula shows packaging discipline.
  - 4 GH Actions workflows: build-standalone, update-catalog, validate-new-provider, validate-skill — same shape COS would want for its registry.
- **Weaknesses**:
  - **15 stars, 2 forks, solo maintainer, 4 months old**. Real bus factor 1 + early-stage churn risk.
  - CI 6/10 failing — daily tag churn aligns with code instability.
  - `.playwright-mcp/console-*.log` files committed (housekeeping concern).
  - Tests exist (`tests/test_aggregate.py` + `test_patterns.py`) but small.
- **Architecture**: Catalog (JSON) + CLI (Python) + per-provider exports + JSON Schemas for validation. Static-site frontend in `docs/`.

### Integration Plan (TRIAL+)
- **What to use**:
  1. `schema/skill-manifest-schema.json` — direct reference for COS skill-manifest JSON Schema (we currently lack one).
  2. `cli/validate.py` patterns for skill validation.
  3. `exports/*.json` per-provider export pattern.
- **How to integrate**: Pattern adoption + selective port. Treat the project as a reference implementation, not a vendored dependency.
- **Effort estimate**: medium (1-2 days to adapt schema + validation patterns to COS conventions)
- **Dependencies it brings**: Python (already in COS); pyproject.toml-based packaging

### Risks
- Bus factor 1; project may go stale.
- Daily-tag cadence + CI red = pre-v1 churn; do not vendor live, copy patterns.
- Small test surface — quality of validation logic untested at scale.

### Cross-Reference vs Shallow Radar
Shallow verdict: "Skill quality-validation + security-scan scoring heuristics for `skill-router` ranking (low stars, novel primitive)." **Deep evidence partially overturns**: the novel primitive is real, but the project is more pre-v1 churn than the shallow note suggested (CI 6/10 failing, daily tag cadence, single solo maintainer with 15★/2 forks). **Downgrade ADOPT-implied → TRIAL.** Action stays the same (port the schema + validation patterns) but mark as reference-only, not adoption-target.

### Raw Metrics Appendix
```
{"name":"agent_skills_directory","license":"MIT","stars":15,"forks":2,"language":"Python","pushed":"2026-04-29T08:34:51Z","created":"2026-01-08T22:50:15Z","open_issues":4,"size":9899 KB}
SKILL.md count: 0 (this is a catalog/aggregator, not a skill-author repo)
tags: v2026.04.29,v2026.04.28,v2026.04.27,v2026.04.25,v2026.04.24
issues_30d=1, CI=4/10 success
```
