---
adr: 318
title: Copy-Only Checkpoints and Stash Quarantine
status: accepted
implementation_status: implemented
date: '2026-05-15'
supersedes: []
superseded_by: null
implementation_files:
- hooks/auto-checkpoint.sh
- rules/stash-quarantine.md
- skills/stash-quarantine/SKILL.md
- scripts/stash_quarantine_audit.py
- tests/integration/test_auto_checkpoint_named_stash.py
- tests/unit/test_stash_quarantine_audit.py
- docs/06-Daily/reports/stash-reference-incident-postmortem-2026-05-15.md
tier: maintainer
classification_basis: copy-only checkpoint implementation, regression tests, and postmortem
  from the stash-reference incident; no remaining in-scope work for this ADR, and
  any future stash tooling is separate/out-of-scope follow-up
tags:
- stash-quarantine
- checkpoints
- session-safety
- governance
---

# ADR-318 — Copy-Only Checkpoints and Stash Quarantine

## Status

Accepted.

## Context

`git stash` is useful as a human emergency tool, but it is a poor default
primitive for an agent operating system. Positional stash refs such as
`stash@{0}` are reflog positions, not identities. They drift whenever another stash is pushed.
Even when stashes are named, a hook that performs a stash round trip can hide
operator WIP if `apply` conflicts, the hook is interrupted, or another hook
mutates the stash stack concurrently.

Cognitive OS already had ADR-221 and ADR-222 for pre-agent snapshot safety:
stash identity must be SHA-first, and pre-agent stash mutation must be deferred
until launch is confirmed. The 2026-05-15 taxonomy/EAS restoration session
exposed a broader operator-workflow issue: using `stash@{n}` conversationally as
if it were a stable work-front identifier creates ambiguity, and PostToolUse
checkpointing still had a legacy stash round-trip path.

## Decision

Cognitive OS checkpoints are **copy-only by default**. Runtime checkpoint hooks
MUST copy dirty file bytes into `.cognitive-os/checkpoints/<checkpoint>/files/`
and write JSON metadata. They MUST NOT mutate `git stash` unless explicitly
opted in by both:

```bash
COS_AUTO_CHECKPOINT_USE_STASH=1
COS_ALLOW_DESTRUCTIVE_GIT=1
```

Stash remains a quarantined compatibility mechanism, not the canonical OS state
store.

## Shared Primitives

ADR-318 is not only an internal hook fix. It also defines shared agentic primitives for any repository using agents:

- `rules/stash-quarantine.md` — contextual rule for stash references, WIP recovery, and work-front isolation.
- `skills/stash-quarantine/SKILL.md` — manual workflow for named quarantine, inspected restore, and durable alternatives.
- `scripts/stash_quarantine_audit.py` — audit tool that flags unsafe stash guidance in docs/code.

These primitives are `SCOPE: both` because the problem appears while maintaining Cognitive OS and while operating adopter projects. The implementation hook remains a Cognitive OS runtime surface, but the doctrine and audit are portable.

## Hard Rules

1. **No implicit stash restore**: OS docs and operator messages must not suggest
   bare `git stash apply`, `git stash pop`, or `git stash drop` without a reviewed
   target.
2. **No positional identity**: `stash@{n}` may appear in tests and forensic
   examples, but persisted state and operational instructions must use stash
   SHA, unique stash subject, or an explicitly reviewed current ref.
3. **Copy before mutate**: checkpointing must preserve WIP by copying files to
   `.cognitive-os/` before any optional legacy stash operation.
4. **Named/SHA lookup for compatibility**: if legacy stash mode is explicitly
   enabled, the hook must name the stash, look it up by subject/current ref, and
   preserve it on apply failure.
5. **Semantic front isolation**: when the operator or an agent separates work
   fronts, the durable unit is a branch/worktree/commit or a named quarantine
   entry. A positional `stash@{n}` is only a transient pointer used after
   inspection.

## Consequences

- Periodic checkpointing can no longer make the visible worktree appear clean by
  default.
- Recovery metadata records copied files and copied bytes instead of pretending a
  stash ref is the source of truth.
- Legacy stash workflows remain possible for emergency compatibility, but they
  are opt-in and visibly marked as legacy.
- Operator instructions become more verbose, but safer: inspect first, then
  apply/drop the reviewed entry.

## Acceptance Criteria

```bash
.venv/bin/python -m pytest tests/integration/test_auto_checkpoint_named_stash.py -q
.venv/bin/python -m py_compile lib/checkpoint_manager.py
bash -n hooks/auto-checkpoint.sh hooks/crash-recovery.sh hooks/stash-budget-warn.sh scripts/stash-leak-alarm.sh
```

The tests must prove default auto-checkpoint mode leaves the stash stack
unchanged, writes copied file metadata, and keeps legacy stash behavior behind an
explicit opt-in.

## Alternatives rejected

- Leave the decision implicit in conversation history: rejected because ADR-gated governance needs a durable, reviewable record with explicit trade-offs.
- Treat this as an unversioned implementation note: rejected because the behavior affects operator-facing contracts and must survive refactors.

## Verification

Implemented on 2026-05-15:

- `hooks/auto-checkpoint.sh` now writes copy-only checkpoints by default.
- `tests/integration/test_auto_checkpoint_named_stash.py` verifies no default
  stash leak and validates checkpoint metadata.
- Operator-facing messages in crash recovery, stash budget warning,
  stash-leak alarm, and checkpoint recovery instructions now require a reviewed
  stash target instead of implicit `stash@{0}`/bare apply/pop/drop.

```bash
.venv/bin/python -m pytest tests/integration/test_auto_checkpoint_named_stash.py tests/unit/test_stash_quarantine_audit.py -q
python3 scripts/stash_quarantine_audit.py --strict
```
