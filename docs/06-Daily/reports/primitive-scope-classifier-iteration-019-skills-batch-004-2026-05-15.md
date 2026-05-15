# Primitive Scope Classifier — Iteration 019: skills sub-batch 004

Date: 2026-05-15

## Goal

Resolve the final 10 `skills/` rows from the declared-`both` `insufficient-metadata` bucket, using the ADR-314 classification rubric row by row.

## Rows

| Skill | Decision | Change | Evidence |
|---|---:|---|---|
| `skills/sdd-resume/SKILL.md` | `both` | shared-surface metadata | SDD pipeline resume/state inspection applies to COS changes and adopter project changes. |
| `skills/security-red-team/SKILL.md` | `os-only` | marker `both` → `os-only`; maintainer metadata | Unified security red-team inventories and scores Cognitive OS primitive surfaces, manifests, hooks, rules, skills, and COS tests. |
| `skills/session-manager/SKILL.md` | `both` | shared-surface metadata | Cognitive OS session list/inspect/cleanup applies to COS source sessions and installed COS sessions in adopter projects. |
| `skills/session-report-executive/SKILL.md` | `both` | shared-surface metadata | Executive session reporting translates COS metrics for COS work and adopter project work. |
| `skills/session-wrapup/SKILL.md` | `both` | shared-surface metadata | End-of-session backlog, Engram, and summary routine applies to COS maintenance and adopter project sessions. |
| `skills/skill-creator/SKILL.md` | `both` | shared-surface metadata | Skill authoring and package scaffolding can create COS source skills and adopter project/package skills. |
| `skills/validate-config/SKILL.md` | `both` | shared-surface metadata | Validates Cognitive OS configuration in COS source and installed/project overlays. |
| `skills/vulnerability-scan/SKILL.md` | `both` | shared-surface metadata | Garak LLM vulnerability scanning applies to COS LLM endpoints and adopter project LLM endpoints. |
| `skills/wiki-ingest/SKILL.md` | `both` | shared-surface metadata | Raw-source to docs-vault ingestion is reusable for COS knowledge docs and adopter project documentation vaults. |
| `skills/worktree-triage/SKILL.md` | `both` | shared-surface metadata | Git worktree/branch triage is repository-agnostic for COS and adopter project worktrees. |

## Result

Actual after classifier regeneration:

- `skills` unknown debt: 10 → 0.
- total unknown debt: 241 → 231.
- `by_suggested_scope`: `both=214`, `os-only=649`, `project=94`, `unknown=231`.
- 1 stale `both` marker corrected to `os-only`.
- 9 confirmed `both` rows gained durable shared-surface metadata.
- Remaining unknown prefixes: `hooks=36`, `rules=80`, `scripts=115`; `skills` is no longer present.

## Next work

With `skills` cleared, continue with another prefix bucket: hooks (36), rules (80), or scripts (115).
