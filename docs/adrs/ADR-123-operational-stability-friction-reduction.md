---
adr: 123
title: Operational Stability and Friction Reduction Program
status: proposed
date: 2026-05-02
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos_repair.py
  - scripts/cos_validate.py
  - lib/validation_lanes.py
tier: standard
tags: [stability, friction-reduction, guards, maturity]
---

# ADR-123: Operational Stability and Friction Reduction Program

## Status

Proposed — 2026-05-02

## Context

Cognitive OS is valuable because it makes multi-agent work safer than a raw
agent harness: it owns WIP, blocks dangerous races, records decisions, protects
main, and turns recurring failures into primitives. The remaining product risk
is not lack of power; it is that operational stability is still medium-high
rather than boringly reliable, and some flows feel too heavy for the actual
risk.

Recent incidents exposed the pattern:

- a hook could create a snapshot/stash before the corresponding restore path was
  guaranteed;
- harmless residue such as copy-only markers looked like active corruption;
- new guards sometimes blocked first and explained repair second;
- full validation was used as a confidence substitute when a smaller lane would
  have been enough;
- agents needed durable primitives such as `branch-worktree-closure` instead of
  remembering conversational instructions.

The SO should behave like a safety system: quiet during low-risk work, strict
when data loss or main corruption is plausible, and always able to explain and
repair its own blockers.

## Decision

Adopt a six-phase Operational Stability and Friction Reduction Program. The
program is tracked in
`.cognitive-os/plans/architecture/operational-stability-friction-reduction.md`
and is governed by these decisions:

1. **Every guard declares maturity.** Guards move through `observe`, `warn`,
   `block`, and `emergency`; new guards cannot default to `block` without tests
   for false positives and production exceptions.
2. **Profiles are risk-adaptive.** `lean`, `standard`, and `strict` profiles are
   chosen by context: branch, dirty state, worktrees, task claims, stashes,
   landing intent, and changed files.
3. **Blocks include repair intent.** A block must include the safe next action,
   preferably a deterministic `cos repair --dry-run` or skill invocation.
4. **Hygiene is not treated as corruption.** Possible WIP loss, stale main, and
   projection drift may block. Stale sessions, clean merged worktrees, and
   copy-only markers should auto-clean or warn.
5. **Status is unified.** Operators and agents get one status surface that says
   whether it is safe to work, launch agents, validate, and push.
6. **Validation lanes are explicit.** Fast, landing, laptop, full, and chaos
   lanes have budgets and diff-based recommendations.
7. **Distribution tiers separate runtime from meta-infrastructure.** ADR-124
   defines `core`, `team`, `maintainer`, and `lab` boundaries so small projects
   can adopt the safety primitives without the full SO-maintainer layer.

The goal is not to remove governance. The goal is to make governance proportional,
self-healing, and modular.

## Consequences

- Agents should experience fewer hard stops during low-risk work.
- High-risk operations become more defensible because strict mode is reserved
  for cases where strictness matters.
- Guard authors must ship tests for legitimate exceptions before enabling block
  mode.
- New CLI/status surfaces will add implementation work, but should reduce
  repeated manual forensics.
- Some existing hooks will need migration from boolean enabled/disabled logic to
  maturity/profile-aware behavior.

## Alternatives rejected

- **Disable the SO for small work**: rejected because even small work can lose
  WIP; the better answer is a lean profile, not no protection.
- **Keep all guards always strict**: rejected because excessive false positives
  train agents and operators to bypass the system.
- **Rely on full `make test-laptop` for confidence**: rejected because full
  validation is expensive and does not by itself prevent live races or stale
  residue.
- **Document repair manually only**: rejected because agents need deterministic
  primitives and commands, not prose they may forget.

## Verification

Each phase must add or update executable validation before being marked done:

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
python3 -m pytest tests/behavior/test_cos_cleanup_preserved_wip.py -q
python3 -m pytest tests/unit/test_codex_guard_layer.py -q
python3 scripts/derived_artifact_gate.py
```

Phase-specific tests are listed in
`.cognitive-os/plans/architecture/operational-stability-friction-reduction.md`.

## 2026-05-05 slice evidence update

ADR-123-S3 adds a dry-run-first `cos repair` surface backed by reversible
preserved-WIP cleanup records and session reaper decisions. ADR-123-S5 adds a
diff-aware validation recommender and merge-queue report fields for recommended
lane, executed lane, and rationale.
