# Skill Router Primitive Routing Post-Mortem — 2026-05-05

## Summary

A local review of uncommitted work uncovered a structural gap in Cognitive OS skill routing: many skills existed on disk but could not be selected by `lib/skill_router.py` from natural-language user prompts. The initial fix added a global coverage ratchet, but the investigation showed the deeper issue is profile-aware primitive projection: a skill only needs router coverage in a given consumer project if that skill is installed or projected for that project's adoption profile.

The immediate correction is a global/full-surface ratchet in `tests/contracts/test_skill_router_coverage.py`. The next correction is to make that ratchet profile-aware across the repo's projection/adoption taxonomies.

## Impact

When a skill exists but is not routeable:

- the orchestrator is less likely to invoke the canonical skill;
- agents write bespoke prompts for work the OS already knows how to do;
- skill investment becomes invisible at runtime;
- profile/install claims can overstate what a downstream project can actually use.

This directly weakens the “agentic primitive” layer because skills become inventory rather than operational affordances.

## What Happened

During review of local uncommitted work, the following metric was raised:

| Metric | Reported value |
|---|---:|
| Skills on disk (`SKILL.md`) | 186 |
| In router and on disk | 78 |
| In router but not on disk | 2 |
| On disk but not in router | 108 |
| Effective coverage | 41.9% |

A live recount after ADR-171/ADR-172/ADR-174 local changes found a slightly different but still critical state:

| Metric | Current local value |
|---|---:|
| Unique skills on disk across `skills/` + `.cognitive-os/skills/` | 185 |
| Primary router entries that resolve to skills on disk | 82 |
| Primary router entries without `SKILL.md` | 1 |
| Skills on disk without primary routing | 103 |
| Effective global coverage | 44.3% |

The remaining primary router orphan is `sdd-new`, which is an intentional SDD meta-command rather than a concrete skill directory.

## Root Cause

### 1. The router was a second source of truth

Most skills self-describe in `SKILL.md`, but the router historically depended on a hand-maintained table in `lib/skill_router.py`. Adding or generating a skill did not force any corresponding router update.

### 2. Tests validated the easier direction

Existing router tests primarily checked that router entries produced expected matches and that routed names were known. They did not prevent a new skill from landing on disk without any route into it.

### 3. Projection profiles were not part of the routing metric

The repo has multiple profile vocabularies:

| Vocabulary | Location | Meaning |
|---|---|---|
| `lean / standard / strict` | `docs/08-References/root/adoption-tiers.md` | User-facing adoption tiers by project/team risk. |
| `default / full` | `cognitive-os.yaml` and `manifests/primitive-projection-profiles.yaml` | Consumer-project projection modes after ADR-093 simplified install profiles. |
| `core / team / maintainer / lab` | `scripts/cos_adoption_profile.py` | Lifecycle-manifest distribution tiers for active primitive surfaces. |

The global count treats every skill on disk as equally routeable. That is useful as a full-surface ratchet, but it is not the right final contract for downstream projects. The correct invariant is:

> For each projection/adoption profile, every installed or projected skill must either be routeable by the SkillRouter or explicitly classified as manual-only, internal, maintainer-only, or backlog.

## Corrections Made

### Global/full-surface contract

Added `tests/contracts/test_skill_router_coverage.py`.

It enforces:

1. Primary router entries must point to skills on disk or explicit meta-command allowlist entries.
2. Skills on disk must be routeable or listed in `manifests/skill-routing-coverage.yaml`.
3. Coverage cannot regress below the current local baseline:
   - `MIN_ROUTED_SKILL_COUNT = 82`
   - `MIN_ROUTED_SKILL_COVERAGE = 44.0`
4. If a skill becomes routeable, the manifest backlog must shrink.
5. If a new skill is added without routing, the contract fails until it is routed or deliberately classified.

### Router API correction

Added `SkillRouter.get_primary_routing_skills()` so tests can distinguish primary routeability from fallback aliases. Fallback commands may be aliases or meta-commands and should not inflate or distort the main coverage metric.

### Frontmatter routing proof

ADR-174 adds `routing_patterns:` support in SKILL.md frontmatter. The first proof-of-concept skills now load through `_load_routing_from_frontmatter()`, and `tests/contracts/test_skill_router_invariant.py` verifies that path.

The advisory hook `hooks/skill-md-routing-validator.sh` warns on SKILL.md writes that omit `routing_patterns:`. It is non-blocking by design; the durable enforcement remains the contract tests and manifest ratchet.

### ADR alignment

Updated `docs/02-Decisions/adrs/ADR-174-auto-derived-primitive-routing.md` so its numbers, tests, and acceptance criteria match the actual local implementation:

- 185 unique skills on disk;
- 82 routeable primary skills;
- 103 unrouteable skills;
- one intentional meta-command orphan (`sdd-new`);
- enforcement in `tests/contracts/test_skill_router_coverage.py`.

### Wiring closure retained

The same review also preserved required wiring corrections from the surrounding local work:

- skill-router observability hooks are allowlisted for the text-scan registration checker;

## What This Does Not Yet Fix

The new contract is global. It does not yet know which skills are projected into a given consumer project profile.

That means it can catch regressions and force explicit backlog classification, but it cannot yet answer:

- “Are all `lean` skills routeable?”
- “Are all `standard` skills routeable?”
- “Are all `strict`/`full`/`maintainer` skills routeable?”
- “Is this skill missing routing because it is maintainer-only or because we forgot it?”

## Required Follow-Up

### 1. Normalize profile vocabulary

Create a machine-readable mapping among:

| User-facing tier | Projection profile | Lifecycle distribution |
|---|---|---|
| Lean | `default` | `core` |
| Standard | `default` plus team extensions | `core` + `team` |
| Strict | `full` | `core` + `team` + `maintainer` |
| Lab | opt-in only | `lab` |

This mapping should live in a manifest rather than prose so tests can consume it.

### 2. Add profile-aware router coverage tests

Add a contract that computes, for each profile:

| Profile | Projected skills | Routeable | Manual/internal/backlog | Coverage |
|---|---:|---:|---:|---:|
| lean/core | TBD | TBD | TBD | target high |
| standard/team | TBD | TBD | TBD | target medium-high |
| strict/full/maintainer | TBD | TBD | TBD | target ratcheted |

The test should fail when a skill is projected into a profile without routing or explicit classification.

### 3. Keep allowlist classification outside Python tests

`manifests/skill-routing-coverage.yaml` is now the machine-readable governance surface for the first ratchet. Keep future classification there instead of hardcoding large exception lists in pytest. Follow-up fields can add profile-specific routing classes such as:

```yaml
routing_class: archived
profiles: []
rationale: ADR-171 rejected the integration.
```

Current file: `manifests/skill-routing-coverage.yaml`.

### 4. Continue ADR-174 migration

For each backlog skill:

1. Add `routing_patterns:` to `SKILL.md` frontmatter when the skill should be discoverable.
2. Remove the skill from the unrouted allowlist.
3. Add an intent-level test when the pattern is non-obvious or high-risk.

## Acceptance Criteria for This Post-Mortem

- `docs/06-Daily/reports/skill-router-primitive-routing-postmortem-2026-05-05.md` exists and is linked from `docs/00-MOCs/entrypoints/README.md`.
- `manifests/skill-routing-coverage.yaml` records the baseline and explicit exceptions outside pytest.
- `tests/contracts/test_skill_router_coverage.py` passes.
- `tests/contracts/test_skill_router_invariant.py` passes.
- `python3 -m pytest tests/unit/test_skill_router.py tests/contracts/test_skill_router_coverage.py -q` passes.
- ADR-174 reflects the current measured baseline and no longer points at missing invariant-test or hook files.

## Verification

Run:

```bash
ruff check lib/skill_router.py tests/unit/test_skill_router.py tests/contracts/test_skill_router_coverage.py
python3 -m pytest tests/unit/test_skill_router.py tests/contracts/test_skill_router_coverage.py -q
```

For broader local confidence, also run:

```bash
python3 -m pytest tests/contracts/test_orchestrator_skill_routing.py \
  tests/unit/test_skill_router_prompt_suggest_hook.py \
  tests/unit/test_orchestrator_decision_trace_hook.py \
  tests/architecture/test_wiring.py -q
```

## Decision

Keep the global/full-surface ratchet as the first guardrail, but do not treat it as the final product metric. The durable product metric is profile-aware routeability: projected skills should be discoverable in the profiles where they are installed.
