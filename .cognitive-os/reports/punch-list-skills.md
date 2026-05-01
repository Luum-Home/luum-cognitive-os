# Punch List — skills bucket

> Generated 2026-05-01 from `docs/reports/aspirational-audit-2026-05-01.md`.
> Baseline: total=667, ASPIRATIONAL=69, dormant_aspirational_ratio=0.3538.
> Scope: all ASPIRATIONAL skills detected in the audit run.

| path | dormant signal | recommended action |
|------|---------------|-------------------|
| `skills/component-reality-check/SKILL.md` | invocations_30d=0, referenced_in_docs=False | IMPLEMENT or PRUNE: no usage. Implement the skill body if planned, or archive to docs/archive/skills/ |
| `skills/coordination-status/SKILL.md` | invocations_30d=0, referenced_in_docs=False | IMPLEMENT or PRUNE: no usage. Wire into RULES-COMPACT.md reference or archive |
| `skills/cost-predictor/SKILL.md` | invocations_30d=0, referenced_in_docs=False | IMPLEMENT or PRUNE: no usage. Skill referenced in cost-governance rule — add reference to RULES-COMPACT.md or archive |
| `skills/docs-execution-audit/SKILL.md` | invocations_30d=0, referenced_in_docs=False | IMPLEMENT or PRUNE: no usage. Archive to docs/archive/skills/ if no immediate need |
| `skills/dogfood-score/SKILL.md` | invocations_30d=0, referenced_in_docs=False | IMPLEMENT: dogfood-score is core to ADR-059 plan. Run it to populate baseline, then reference in rules |
| `skills/domain-model/SKILL.md` | invocations_30d=0, referenced_in_docs=False | IMPLEMENT or PRUNE: no usage. Archive to docs/archive/skills/ if no immediate need |
| `skills/install-recommended/SKILL.md` | invocations_30d=0, referenced_in_docs=False | IMPLEMENT or PRUNE: no usage. Archive to docs/archive/skills/ if no immediate need |
| `skills/invariant-check/SKILL.md` | invocations_30d=0, referenced_in_docs=False | IMPLEMENT or PRUNE: no usage. Archive to docs/archive/skills/ if no immediate need |
| `skills/ops-runbook/SKILL.md` | invocations_30d=0, referenced_in_docs=False | IMPLEMENT or PRUNE: no usage. Archive to docs/archive/skills/ if no immediate need |
| `skills/risk-register/SKILL.md` | invocations_30d=0, referenced_in_docs=False | IMPLEMENT or PRUNE: no usage. Archive to docs/archive/skills/ if no immediate need |

## Action Summary

| action | count |
|--------|-------|
| IMPLEMENT (complete skill body + reference in docs) | 1 (dogfood-score — ADR-059 required) |
| IMPLEMENT or PRUNE (decide per sprint) | 9 |

Priority: `skills/dogfood-score/SKILL.md` is tracked by ADR-059 as a measurement tool.
Implement it or wire the existing `scripts/dogfood-score.py` invocation into the skill body.
