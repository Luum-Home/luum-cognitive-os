---
adr: 149
title: Primitive Duplication Audit
status: accepted
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - scripts/primitive_duplication_audit.py
  - tests/unit/test_primitive_duplication_audit.py
  - docs/architecture/primitive-duplication-audit.md
  - docs/architecture/primitive-duplication-audit-implementation-plan.md
  - docs/manual-tests/primitive-duplication-audit.md
tier: maintainer
tags: [primitive-readiness, duplication, refactoring, acc, projection]
---

# ADR-149: Primitive Duplication Audit

## Status

**Accepted** — 2026-05-04

## Context

Cognitive OS already has partial duplication controls, but they are split by surface:

- `scripts/docs_duplicate_audit.py` detects near-duplicate Markdown documentation.
- `scripts/component-lint.sh` detects duplicate descriptions in selected catalog surfaces.
- `scripts/primitive_lifecycle.py` detects duplicate primitive IDs.
- `scripts/precommit_content_hash.py` warns about duplicate commits/content hashes.
- `scripts/cos_primitive_harvester.py` can recommend invoking an existing primitive instead of creating another one.
- `scripts/lint-shell.sh` improves Bash quality so repeated shell patterns become easier to see.

Those controls do not answer the maintainer question we now need for SO evolution: when Bash, Python, YAML/config, rules, skills, hooks, or docs repeat behavior, should the behavior move to a shared helper, a manifest/profile, a template, a rule, a skill, or remain duplicated for isolation and portability?

## Decision

Add `scripts/primitive_duplication_audit.py` as the first unified duplication audit for agentic primitive and configuration surfaces. The audit is dependency-free and emits both machine-readable and human-readable reports:

- `docs/reports/primitive-duplication-latest.json`
- `docs/reports/primitive-duplication-latest.md`

The audit classifies findings into SO-specific categories:

| Kind | Meaning | Default common home |
|---|---|---|
| `exact-copy` | Normalized file content is identical. | `templates/ or lib/` |
| `near-copy` | Token shingles are highly similar. | `templates/ or lib/` |
| `yaml-structural-repeat` | YAML/config files share a structural schema. | `manifests/` |
| `bash-function-repeat` | Shell functions have identical normalized bodies. | `hooks/_lib/` or `scripts/_lib/` |
| `python-function-repeat` | Python functions have identical AST bodies. | `lib/` |
| `primitive-overlap` | Rule/skill procedure text is highly similar. | `skills/ or rules/` |

Every finding must include a recommendation, proposed common home, and consumer relevance. This is intentionally advisory in reconstruction: it exposes extraction opportunities without auto-refactoring or blocking CI by default.

The ACC pipeline should run the audit as an adapter during refresh so duplication debt is visible next to readiness/projection debt.

## Consequences

### Positive

- Maintainers get a single report for repeated Bash/Python/YAML/config/primitive patterns.
- Findings are actionable because they suggest where common behavior should live.
- Consumer-project relevance is explicit, so projected primitives are not refactored only from an SO-local viewpoint.
- ACC can surface duplication debt without making duplicate detection a hard gate too early.

### Negative

- The first implementation is heuristic and can produce false positives.
- Near-copy detection can become expensive if thresholds or include paths are widened too far.
- Some duplication is intentional for harness isolation; the report requires human triage before extraction.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Use only `jscpd` or PMD CPD | They detect clones but do not understand Cognitive OS common homes, projection classes, or primitive boundaries. |
| Extend only `docs_duplicate_audit.py` | Documentation duplicate detection is too narrow for Bash/Python/YAML/config and primitive overlap. |
| Immediately block CI on any duplicate | Rejected during reconstruction because the first scan should build a baseline before becoming a gate. |
| Auto-extract repeated code | Rejected because extraction can change portability and harness behavior. |

## Verification

```bash
python3 -m pytest tests/unit/test_primitive_duplication_audit.py -q
python3 scripts/primitive_duplication_audit.py --project-root . --json
python3 -m py_compile scripts/primitive_duplication_audit.py scripts/acc_pipeline.py
```

## Implementation Evidence

- Implemented in `scripts/primitive_duplication_audit.py`: unified duplicate detection and JSON/Markdown report generation.
- Implemented in `tests/unit/test_primitive_duplication_audit.py`: Python, Bash, YAML, and CLI report coverage.
- Documented in `docs/architecture/primitive-duplication-audit.md` and `docs/manual-tests/primitive-duplication-audit.md`.
