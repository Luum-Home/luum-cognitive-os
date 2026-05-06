---
evaluated_at: 2026-05-06 06:50 UTC
evaluation_level: 2
parent_radar: docs/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (Harness builder focused on deterministic/repeatable AI coding)
deep_verdict: TRIAL — strong patterns but TS-only and pre-1.0; pattern adoption only
deepwiki_url: https://deepwiki.com/coleam00/Archon
engram_id: pending
---

## Repository Evaluation: coleam00/Archon

### Classification: TRIAL
**Score**: 7.7/10
**Evaluation Level**: 2 (Deep — gh api tree, packages/ + .archon/ + .claude/ inspection)

### Summary
"The first open-source harness builder for AI coding. Make AI coding deterministic and repeatable." TypeScript monorepo, MIT, 20k★, push 2026-05-04, v0.3.10 in active 0.3.x line. Recursive curiosity: Archon (a harness builder) has its own `.claude/skills/` tree — `archon-dev`, `playwright-cli`, `release`, `replicate-issue`, `rulecheck`, `save-task-list`, `triage`, `validate-ui`, `test-release` — making it a real-world example of dogfooded skills + workflows. Notable structure: `.archon/{commands,scripts,workflows}` defines the harness primitives; `packages/` provides core/cli/server/web/adapters/providers/git/isolation. **TRIAL** because pre-1.0 + TS-only + complex monorepo means pattern lifting is the right scope.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 8/10 | Harness builder + workflow primitives map onto COS orchestration; multi-adapter (slack, telegram, discord, gitea, gitlab, github) is broader than COS |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 9/10 | Push 2026-05-04; v0.3.6-v0.3.10 cadence; 100+ issues/30d |
| Maturity | 15% | 6/10 | v0.3.x pre-1.0; 1.25 years old; 245 open issues |
| Integration | 10% | 5/10 | TS monorepo; clean packages/ but not directly importable from COS Python |
| **Weighted Total** | | **8.0/10** weighted, presented as **7.7/10** after TS-only adjustment | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 100+ (paged out) | high issue activity |
| Release cadence | v0.3.6-v0.3.10 | biweekly releases |
| CI health | 3/10 success | CI mostly red (likely cancelled-from-PR-cycles) |

### Key Findings
- **Strengths**:
  - **Recursive dogfooding**: Archon-the-harness-builder has its own .claude/skills tree — concrete reference for what "harness builder uses harness builder's skills" looks like.
  - **Workflow primitives**: `.archon/workflows/{defaults, experimental, maintainer, test-workflows}` + `.archon/commands/defaults` define a workflow grammar. Compare against COS skill+rule system.
  - **Multi-adapter breadth**: chat (slack, telegram, discord), forge (github, gitea, gitlab) — broader than COS. Pattern reference for any multi-platform expansion.
  - Clean monorepo: `packages/{adapters, cli, core, docs-web, git, isolation, paths, providers, server, web, workflows}`.
  - PRP (Project Reference Prompt) primitives in `.claude/PRPs/issues/{,completed}` show structured task tracking.
- **Weaknesses**:
  - 245 open issues + pre-1.0 = managed but not stable.
  - TS-only — Python COS would need to translate patterns.
  - "Harness builder" overlaps Archon ↔ COS in confusing ways (we'd be building on a thing that builds harnesses).
  - 3.18k forks vs 20k stars on a 1.25-year-old repo = healthier ratio than the metric-pump cohort.
- **Architecture**: Monorepo with packages/ split; .archon/ as the canonical harness-config directory; packages/workflows + packages/orchestrator as the engine; multi-adapter for chat + forge.

### Integration Plan (TRIAL+)
- **What to use**:
  1. **Workflow grammar** in `.archon/workflows/` and `packages/workflows/src/{defaults, schemas}` — pattern reference for COS skill+task DAGs.
  2. **PRP pattern** in `.claude/PRPs/` — structured issue tracking for COS sprint discipline.
  3. **Forge adapters** (`packages/adapters/src/{forge, community/forge}`) — pattern reference for any multi-Git-host support.
  4. **rulecheck skill** in `.claude/skills/rulecheck/hooks/` — direct compare against COS rule-enforcement hooks.
- **How to integrate**: Pattern lifting only. Do not depend on Archon as a library.
- **Effort estimate**: medium (3-5 days for workflow grammar + PRP pattern study)
- **Dependencies it brings**: none (pattern adoption)

### Risks
- TS-only adds translation friction.
- Pre-1.0 → API churn.
- "Harness builder of harness builder" overlap may cause architectural confusion if Archon is treated as a dependency.

### Cross-Reference vs Shallow Radar
Shallow verdict: "Harness builder focused on deterministic/repeatable AI coding." **Deep evidence agrees and adds a finding**: Archon's recursive dogfooding (its own `.claude/skills/` tree) is a stronger pattern signal than the shallow note suggested. The TS-only + pre-1.0 combination remains the limiting factor. **Hold ADOPT-implied at TRIAL** — pattern adoption is the right scope.

### Raw Metrics Appendix
```
{"name":"Archon","license":"MIT","stars":20867,"forks":3183,"language":"TypeScript","pushed":"2026-05-04T20:40:38Z","created":"2025-02-07T21:04:12Z","open_issues":245,"size":17521 KB}
tags: v0.3.10,v0.3.9,v0.3.8,v0.3.7,v0.3.6
issues_30d=100+, CI=3/10 success
```
