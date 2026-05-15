# Primitive Scope Classifier — Iteration 018: skills sub-batch 003

Date: 2026-05-15

## Goal

Resolve the third 10 `skills/` rows from the remaining declared-`both` `insufficient-metadata` bucket, using the ADR-314 classification rubric row by row.

## Rows

| Skill | Decision | Change | Evidence |
|---|---:|---|---|
| `skills/peer-card/SKILL.md` | `both` | shared-surface metadata | Curated personal/user memory via Engram is usable while maintaining COS and while working in adopter projects. |
| `skills/preserved-wip-cleanup/SKILL.md` | `both` | shared-surface metadata | Archive-first git stash/worktree cleanup is repository-agnostic for COS and adopter project worktrees. |
| `skills/primitive-harvester/SKILL.md` | `both` | shared-surface metadata | Conversation-to-primitive harvesting governs reusable workflows in COS source and adopter project overlays. |
| `skills/queue-drain/SKILL.md` | `os-only` | marker `both` → `os-only`; maintainer metadata | Drains COS agent dispatch queues and health checks via COS queue libraries, not a generic project primitive. |
| `skills/red-team/SKILL.md` | `both` | shared-surface metadata | Prompt injection/jailbreak testing applies to COS prompts and adopter project agent prompts. |
| `skills/redteam-harness/SKILL.md` | `os-only` | marker `both` → `os-only`; maintainer metadata | Runs COS red-team scenarios against agent OS false-done/unwired-constant failure modes and COS test fixtures. |
| `skills/resource-governor/SKILL.md` | `both` | shared-surface metadata | Resource and budget optimization reads COS metrics but applies to COS maintenance and adopter project work. |
| `skills/run-tests/SKILL.md` | `both` | shared-surface metadata | Test runner has COS-specific fast path and generic project framework fallback, so it is shared. |
| `skills/scaffold-project/SKILL.md` | `project` | marker `both` → `project`; consumer metadata | Scaffolds project-local `.claude` rules/skills/hooks from detected-stack for adopter projects; COS source construction does not require it. |
| `skills/sdd-continue/SKILL.md` | `both` | shared-surface metadata | SDD continuation/state inspection is used for COS changes and adopter project changes. |

## Result

Actual after classifier regeneration:

- `skills` unknown debt: 20 → 10.
- total unknown debt: 251 → 241.
- `by_suggested_scope`: `both=205`, `os-only=648`, `project=94`, `unknown=241`.
- 2 stale `both` markers corrected to `os-only`.
- 1 stale `both` marker corrected to `project`.
- 7 confirmed `both` rows gained durable shared-surface metadata.

## Next work

Continue with the final 10 `skills/` rows, preserving the same rubric and avoiding global marker rewrites.
