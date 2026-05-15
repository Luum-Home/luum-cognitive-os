# Primitive Scope Classifier — Iteration 015: template sub-batch

Date: 2026-05-15

## Goal

Resolve the smallest remaining `insufficient-metadata` sub-batch: 8 templates declared `both` without lifecycle / consumer-availability metadata.

## Decision

All 8 templates remain `both`. They are reusable prompt/procedure/test templates for COS source work and adopter-project work. This iteration only added durable distribution metadata; no markers were changed.

## Rows

| Template | Decision | Evidence |
|---|---|---|
| `templates/adr-template.md` | `both` | Generic ADR decision template usable for COS decisions and adopter project architecture decisions. |
| `templates/agent-research-only.md` | `both` | Research-only agent prompt template applies to COS research tasks and adopter project research phases. |
| `templates/contracts/test_redteam_baseline.template.py` | `both` | Consumer-customizable red-team baseline template mirrors COS red-team contracts. |
| `templates/cross-harness-authoring.md` | `both` | Cross-harness authoring template governs portable primitive authoring in COS source and project overlays. |
| `templates/error-recovery.md` | `both` | Generic error recovery template for agentic coding tasks. |
| `templates/prompt-hooks/assumption-tracker-prompt.md` | `both` | Repo-agnostic prompt hook template for assumption counting. |
| `templates/prompt-hooks/scope-creep-prompt.md` | `both` | Repo-agnostic prompt hook template for scope checking. |
| `templates/quality-gates.md` | `both` | Generic quality gate template for COS and project development. |

## Result

```json
{
  "before_unknown": 279,
  "after_unknown": 271,
  "templates_remaining_unknown": 0,
  "by_suggested_scope": {
    "both": 184,
    "os-only": 642,
    "project": 91,
    "unknown": 271
  }
}
```

## Remaining work

Only declared-`both` insufficient metadata remains:

```json
{
  "hooks": 36,
  "rules": 80,
  "scripts": 115,
  "skills": 40
}
```

Recommended next sub-batch: `skills` (40), because they are more semantically explicit than hooks/scripts and smaller than rules.
