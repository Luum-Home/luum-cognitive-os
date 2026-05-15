# Primitive Scope Classifier — Iteration 016: skills sub-batch 001

Date: 2026-05-15

## Goal

Resolve the first 10 `skills/` rows from the remaining declared-`both` `insufficient-metadata` bucket, using the ADR-314 classification rubric before changing any markers.

## Rubric applied

Classification asks where the primitive is required for correct runtime / authoring decisions:

- `os-only`: required to construct, validate, release, document, or operate Cognitive OS itself.
- `both`: repository-agnostic agentic behavior useful in COS and adopter projects.
- `project`: consumer-project-only behavior, unnecessary for COS construction / validation / operation.
- metadata gaps remain `unknown`; they do not justify marker rewrites.

## Rows

| Skill | Decision | Change | Evidence |
|---|---:|---|---|
| `skills/add-rule/SKILL.md` | `os-only` | marker `both` → `os-only`; maintainer metadata | Creates Cognitive OS rule files, updates COS rule indexes/symlinks, and is only required by COS maintainers. |
| `skills/agent-dashboard/SKILL.md` | `os-only` | marker `both` → `os-only`; maintainer metadata | Inspects Claude/COS background-agent runtime internals via local task directories and COS monitoring library. |
| `skills/analyze-improvements/SKILL.md` | `both` | shared-surface metadata | Read-only improvement analysis applies to COS metrics and adopter project COS metrics / project-local skill feedback. |
| `skills/apply-improvements/SKILL.md` | `both` | shared-surface metadata | Approved self-improvement application can update COS rules/skills/templates and adopter project overlays under a human gate. |
| `skills/branch-worktree-closure/SKILL.md` | `both` | shared-surface metadata | Git branch/worktree closure protocol is repository-agnostic for COS and adopter project agent worktrees. |
| `skills/catalog-full/SKILL.md` | `both` | shared-surface metadata | Full skill catalog lookup is useful for COS source catalogs and installed/project skill catalogs. |
| `skills/caveman-compress/SKILL.md` | `both` | shared-surface metadata | Natural-language memory compression is reusable for COS memory files and adopter project memory/preferences files. |
| `skills/caveman-es/SKILL.md` | `both` | shared-surface metadata | Spanish concise communication mode is repo-agnostic agent behavior for COS and adopter projects. |
| `skills/caveman/SKILL.md` | `both` | shared-surface metadata | Concise communication mode is repo-agnostic agent behavior for COS and adopter projects. |
| `skills/compat-test/SKILL.md` | `both` | shared-surface metadata | Model/COS compatibility smoke test applies to COS development and installed COS behavior inside adopter projects. |

## Result

Actual impact after classifier regeneration:

- `skills` unknown debt: 40 → 30.
- total unknown debt: 271 → 261.
- `by_suggested_scope`: `both=192`, `os-only=644`, `project=91`, `unknown=261`.
- 2 stale `both` markers corrected to `os-only`.
- 8 confirmed `both` rows gained durable shared-surface metadata.
- `conflicting-metadata` remains 0 after setting os-only lifecycle rows to maintainer distribution.

## Next work

Continue with the next 10 `skills/` rows, but keep using the rubric row by row.
