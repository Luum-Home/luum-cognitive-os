---
adr: 177
title: Activate Skill Lifecycle Promotion Ladder
status: accepted
date: 2026-05-06
supersedes: []
superseded_by: null
implementation_files:
  - lib/skill_lifecycle_promoter.py
  - lib/doctrine_proposer.py
  - scripts/cos_doctrine_proposer.py
  - scripts/run_skill_lifecycle_promotion_smoke.py
  - tests/unit/test_skill_lifecycle_promoter.py
  - tests/unit/test_doctrine_proposer.py
  - tests/behavior/test_skill_lifecycle_promotion_ladder.py
tier: maintainer
tags: [skills, lifecycle, promotion, doctrine, dogfood]
---
# ADR-177: Activate Skill Lifecycle Promotion Ladder

## Status

Accepted.

## Context

Cognitive OS already has a coherent lifecycle ladder for agentic primitives:
sandbox, advisory, blocking, demoted, and archived. The doctrine allows
sandbox auto-apply because sandbox is quarantine, but rejects direct auto-apply
into production-grade `SKILL.md` routing surfaces.

The dormant gap was promotion. Auto-generated skills could accumulate in
sandbox without becoming advisory candidates, which made the SO generate new
skills without maturing them into the canonical routing surface. That also made
skill coverage misleading: raw sandbox volume is not the same as advisory or
blocking routing coverage.

ADR-176 SkillStore adoption provides the usage evidence needed by this ladder.
ADR-177 activates the consuming side: evidence can generate lifecycle proposals,
but proposals remain review-only until an operator approves them.

## Decision

Add a propose-only skill lifecycle promotion evaluator.

Sandbox skills are eligible for advisory-promotion proposals when they meet all
of these default thresholds:

1. at least 50 invocations in the last 30 days;
2. at least 5 successful judged-usefulness feedback events;
3. success rate of at least 80% among available judged feedback.

Advisory skills with no recent usage evidence over the demotion window can
generate demotion proposals.

The evaluator may generate doctrine proposals and metrics events. It may not:

- move a skill directory;
- edit production-grade `SKILL.md` files;
- rewrite routing canon;
- promote sandbox skills without human approval.

The doctrine proposer now includes skill lifecycle evidence in
`activate-skill-lifecycle-promotion-ladder` proposals and appends generation
events to `.cognitive-os/metrics/lifecycle-promotion-proposals.jsonl` when it
writes proposal markdown.

## Consequences

### Positive

- Sandbox auto-apply remains compatible with COS doctrine because promotion is
  gated by evidence and operator approval.
- SkillStore-compatible metrics become useful lifecycle evidence instead of
  passive telemetry.
- Dogfood skill coverage can improve by maturing useful sandbox skills, not by
  counting raw sandbox inventory.
- Stale advisory skills get an explicit demotion path instead of becoming
  ambient routing debt.

### Negative / Trade-offs

- Proposal volume may grow if thresholds are too low.
- A skill with many invocations but no judged feedback will not promote until
  operators record usefulness evidence.
- This activates review pressure, not autonomous self-building.

## Acceptance Criteria

```bash
python3 -m pytest tests/unit/test_skill_lifecycle_promoter.py tests/unit/test_doctrine_proposer.py -q
python3 -m pytest tests/behavior/test_skill_lifecycle_promotion_ladder.py -q
python3 scripts/run_skill_lifecycle_promotion_smoke.py
```

Manual smoke must verify:

1. a realistic sandbox skill crossing the thresholds produces a proposal;
2. generated markdown has `runtime_effect: none`;
3. the proposal event is logged;
4. the sandbox skill remains in place;
5. no canonical skill path is created.

## Verification

Implemented and tested on 2026-05-06 with targeted unit, behavior, and isolated
smoke lanes.

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

## Alternatives rejected

- **Leave the decision implicit** — rejected because ADR slots must remain self-describing and audit-safe after multi-agent collision recovery.

