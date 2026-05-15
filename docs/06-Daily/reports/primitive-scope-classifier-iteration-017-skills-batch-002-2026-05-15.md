# Primitive Scope Classifier — Iteration 017: skills sub-batch 002

Date: 2026-05-15

## Goal

Resolve the second 10 `skills/` rows from the remaining declared-`both` `insufficient-metadata` bucket, using the ADR-314 classification rubric row by row.

## Rows

| Skill | Decision | Change | Evidence |
|---|---:|---|---|
| `skills/component-classifier/SKILL.md` | `os-only` | marker `both` → `os-only`; maintainer metadata | Classifies primitives as COS kernel vs package and is required for COS maintainer architecture, not adopter project behavior. |
| `skills/cost-predictor/SKILL.md` | `both` | shared-surface metadata | Task cost prediction uses COS metrics but applies to COS maintenance and adopter project work. |
| `skills/deep-tool-research/SKILL.md` | `both` | shared-surface metadata | Canonical external-tool evaluation is reusable for COS and adopter project tool adoption; COS paths are comparison anchors, not exclusive runtime requirements. |
| `skills/detect-patterns/SKILL.md` | `os-only` | marker `both` → `os-only`; maintainer metadata | Detects rot in the Cognitive OS primitive/codebase mesh and calls COS pattern detector internals. |
| `skills/detect-stack/SKILL.md` | `project` | marker `both` → `project`; consumer metadata | Scans an adopter project root and writes detected-stack.json for project initialization; COS source construction does not require it. |
| `skills/doc-review-personas/SKILL.md` | `both` | shared-surface metadata | Multi-persona documentation review is domain-agnostic and applies to COS docs and adopter project docs. |
| `skills/eval-repo/SKILL.md` | `both` | shared-surface metadata | Deprecated repo-scout alias preserves a repository evaluation workflow usable by COS and adopter projects. |
| `skills/generate-config/SKILL.md` | `project` | marker `both` → `project`; consumer metadata | Generates cognitive-os.yaml from detected stack for adopter project initialization; COS source construction does not require it. |
| `skills/invariant-check/SKILL.md` | `both` | shared-surface metadata | ADR/lib invariant checks apply to COS architecture/code and any adopter project with design docs plus implementation constants. |
| `skills/llm-status/SKILL.md` | `both` | shared-surface metadata | LLM dispatch transparency applies to the current COS install in COS maintenance and adopter projects. |

## Result

Actual after classifier regeneration:

- `skills` unknown debt: 30 → 20.
- total unknown debt: 261 → 251.
- `by_suggested_scope`: `both=198`, `os-only=646`, `project=93`, `unknown=251`.
- 2 stale `both` markers corrected to `os-only`.
- 2 stale `both` markers corrected to `project`.
- 6 confirmed `both` rows gained durable shared-surface metadata.

## Next work

Continue with the next 10 `skills/` rows, preserving the same rubric and avoiding global marker rewrites.
