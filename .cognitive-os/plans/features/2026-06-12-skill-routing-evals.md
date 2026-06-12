---
title: Skill Routing Evals for Plan Feature Boundaries
type: feature
status: draft
score: 45
created: 2026-06-12
author: agent
service: skill-routing
audience: both
---

# Feature: Skill Routing Evals for Plan Feature Boundaries

## Context

the provided `evals.md` download defines six routing evals for
`plan-feature`: two positive, two negative, and two adjacent/boundary cases. The
source file is useful, but it assumes a Claude-only location/schema
(`.claude/skills/benchmarks/evals-schema.md`) and mentions project-specific skill
names that do not map exactly to this repository (`plan-bug-resolution`,
`plan-design-system-component`, `implement-approved-plan`).

Cognitive OS already has `lib/skill_router.py` and unit tests in
`tests/unit/test_skill_router.py`, but no durable, portable eval-case format that
can ingest external markdown cases, normalize skill aliases, and verify routing
boundaries as data. Recent skill-adoption work established the pattern: extract
the reusable behavior, avoid hardcoded stack/harness assumptions, add tests, and
register evidence.

External eval guidance reinforces this split: agent evals should combine
code-based/model/human graders when needed, but routing boundary checks are best
kept as cheap code-based regression tests first. OpenAI's eval guidance frames
evals as structured tests for reliability despite model variability, and
Anthropic's agent eval guidance separates grader types so deterministic checks
can own deterministic routing behavior.

## Approach

Build a portable skill-routing eval feature with a deterministic first slice:

1. Define a repo-native eval case schema that can represent positive, negative,
   and adjacent routing cases without depending on Claude-specific directories.
2. Add a parser/importer for markdown eval cases like the provided `evals.md`.
3. Normalize legacy/source skill aliases to current COS skills.
4. Run cases against `lib.skill_router.SkillRouter` as a code-based grader.
5. Store the adapted eval dataset under a repo-owned path, not under `.claude/`.
6. Add focused regression tests for the `plan-feature` boundaries in the source
   evals.

This is not a replacement for model-based trajectory evals, Promptfoo, DeepEval,
or Strands Evals. It is the cheap deterministic layer that should run before
heavier eval systems.

## Affected Files

### Existing files to inspect or update

- `lib/skill_router.py` — target routing implementation under evaluation.
- `tests/unit/test_skill_router.py` — existing router regression suite.
- `skills/plan-feature/SKILL.md` and `packages/sdd-compound/skills/plan-feature/SKILL.md` — target skill metadata and behavior.
- `packages/sdd-compound/skills/plan-chore/SKILL.md` — expected boundary skill for dependency/maintenance requests.
- `skills/skill-creator/SKILL.md` — precedent for strict portable frontmatter + metadata.
- `scripts/generate_compact_catalog.py` and `skills/CATALOG*.md` — only if routing metadata changes require catalog regeneration.

### New files

- `tests/fixtures/skill-routing-evals/plan-feature-boundaries.md` — adapted source cases in repo-native, portable markdown.
- `lib/skill_routing_evals.py` or `scripts/skill-routing-evals` — parser/runner for eval cases.
- `tests/unit/test_skill_routing_evals.py` — parser/runner tests and the six adapted cases.
- Optional later: `docs/09-Quality/testing/skill-routing-evals.md` if the feature graduates beyond test-only usage.

## Tasks

### Task 1: Define portable routing eval schema

- Create a minimal schema supporting:
  - `id`
  - `category`: `positive | negative | adjacent`
  - `prompt`
  - `expected_skill`
  - `allowed_secondary_skills`
  - `success_criteria`: initially `first-fire`
  - `anti_behaviors`
  - `rationale`
- Keep it markdown-friendly and JSON/YAML-exportable.
- Do not require `.claude/skills/benchmarks` or any harness-specific path.

**Done when:** parser can load all six source cases after adaptation.

### Task 2: Add alias normalization

Normalize source names to current COS names before scoring:

| Source name | Current COS mapping | Reason |
|---|---|---|
| `plan-feature` | `plan-feature` | Existing package-backed skill. |
| `plan-chore` | `plan-chore` | Added in this session as portable chore plan skill. |
| `plan-bug-resolution` | `plan-bug` | Existing COS skill name is `plan-bug`. |
| `implement-approved-plan` | unresolved/blocked initially | No exact current routing target confirmed in this plan. |
| `create-linear-ticket` / `refine-linear-ticket` | optional external aliases | Treat as anti-behavior labels, not required route names unless present. |
| `plan-design-system-component` | unresolved/adjacent | Do not create from this plan; record as boundary gap. |

**Done when:** unresolved names are reported as explicit fixture warnings instead
of silent failures.

### Task 3: Implement deterministic runner

- Instantiate `SkillRouter`.
- For each eval:
  - call `router.match(prompt)` and `router.best_match(prompt)`;
  - compare first match to `expected_skill` for `first-fire` cases;
  - ensure anti-behavior skills are absent or lower-ranked according to case rules;
  - allow secondary skills only for adjacent cases.
- Emit JSON and markdown summaries for local debugging.

**Done when:** runner returns non-zero on failed expectations and prints per-case
reasoning.

### Task 4: Adapt the six provided plan-feature cases

Adapt cases from the provided `evals.md` download:

1. `push-notifications-positive`
2. `mvp-ticket-trigger`
3. `login-500-negative`
4. `nextjs-upgrade-negative`
5. `badge-refactor-adjacent`
6. `push-notifications-english-adjacent`

Keep Spanish and English prompts. Do not hardcode project-only assumptions such
as `ai/plans/features/` as the only valid output path; accept current COS paths
or make output-path assertions conditional by target skill.

**Done when:** all six cases are present in the repo fixture and covered by tests,
with unresolved adjacent targets documented.

### Task 5: Fix routing or metadata only after evals expose a failure

If the adapted evals fail:

- Prefer metadata/routing-intent fixes in the relevant skill over broad regexes.
- Avoid language-specific regex sprawl; use semantic descriptions where the router
  supports them.
- Keep negative-context guards for bug/chore/feature boundaries.
- Add focused unit tests for the exact failure before changing router behavior.

**Done when:** all adapted cases pass or are marked expected-fail with a tracked
reason and follow-up plan.

### Task 6: Register evidence if the runner becomes a primitive

If the runner is added as a script or skill-visible primitive:

- Register it in `manifests/primitive-lifecycle.yaml`.
- Add `.ai` overlay/projection if consumer-visible.
- Add `cos-registry-lock` updates.

If it remains test-only helper code under `tests/`, lifecycle registration is not
needed.

## Test Strategy

### Unit tests

- Parser accepts markdown fixture and rejects malformed cases with useful errors.
- Alias normalization maps known legacy/source names.
- Runner grades first-fire positives and negatives deterministically.
- Unknown expected skill names produce explicit warnings/errors.

### Behavior tests

- Run the six adapted evals against `SkillRouter`.
- Include Spanish and English prompts.
- Include boundary cases for bug/chore/design-system adjacency.

### Regression gates

- `.venv/bin/python -m pytest tests/unit/test_skill_routing_evals.py -q`
- `.venv/bin/python -m pytest tests/unit/test_skill_router.py -q`
- `python3 scripts/primitive_scope_classifier.py --project-dir . --paths <new primitive path> --fail-contradictions` only if a new primitive path is created.

## Risks

- **Current router may not route to `plan-feature`.** Existing tests show feature
  requests often map to `/sdd-new`; the plan must decide whether `plan-feature`
  is intended as the new planning route or whether evals should target current
  COS routing reality.
  - Mitigation: make first run diagnostic; do not rewrite router until the
    product decision is explicit.
- **Source evals reference non-existent skills.**
  - Mitigation: alias known names and surface unresolved names as explicit gaps.
- **Regex overfitting.**
  - Mitigation: add semantic/routing metadata where possible; keep regexes only
    for deterministic aliases such as ticket IDs.
- **Harness coupling.**
  - Mitigation: keep dataset under repo/test fixtures, not `.claude/`, and avoid
    assuming Claude command semantics.

## Rollback Plan

- Revert the fixture, runner, and tests as one commit if the direction is wrong.
- If router metadata changes are made, keep them in a separate commit from the
  eval harness so they can be reverted independently.
- No production runtime state or project-consumer files are mutated by this plan.

## Self-Evaluation

| Category | Score | Justification |
|---|---:|---|
| Completeness | 9/10 | Covers schema, parser, aliasing, runner, cases, tests, and registration boundary. |
| Feasibility | 9/10 | Builds on existing `SkillRouter` and pytest; no external service required. |
| Risk Assessment | 9/10 | Main risks are identified: current `/sdd-new` routing, missing skill aliases, overfitting. |
| Architecture Alignment | 9/10 | Keeps evals deterministic/test-first and avoids harness-specific paths. |
| Test Coverage Plan | 9/10 | Includes parser, runner, alias, behavior, and router regression tests. |

**Total: 45/50**

## Recommendation

Approve as a diagnostic-first feature slice. The first implementation should land
the portable eval harness and adapted fixture, then report whether current router
behavior matches the desired `plan-feature` contract before changing routing.
