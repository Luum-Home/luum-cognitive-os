# Post-Mortem — Positional Stash Reference Confusion During Primitive Restoration

**Date**: 2026-05-15  
**Severity**: P2 operator-trust / workflow-safety  
**Status**: Closed by ADR-318 implementation

## Summary

During the primitive taxonomy/EAS restoration session, work fronts were isolated
with named Git stashes. The assistant later referred to `stash@{0}` / `stash@{1}`
as if those were stable identities. The user correctly challenged whether that
form of work isolation belongs to Cognitive OS.

The answer is architectural:

- `stash@{n}` is Git positional syntax, not an OS primitive.
- Work-front isolation and WIP preservation are OS concerns.
- Therefore Cognitive OS must support the workflow, but must not encode
  positional stash refs as durable state or operator guidance.

## Impact

- The operator had to question whether SO primitives/tools were being treated as
  outside the SO because they were temporarily stashed.
- The phrasing blurred two different concepts: semantic commit scope vs. OS
  ownership of the primitive/tool front.
- Positional stash references could have caused the wrong front to be restored if
  used later without inspection.

## Root Cause

The immediate root cause was sloppy operator language: using `stash@{n}` as a
shorthand for a work front.

The systemic root cause was that parts of the OS and its messages still treated
stash as a normal recovery surface, even though prior incidents had already shown
stash mutation and positional refs are fragile under agents and concurrent hooks.

## What Went Well

- Work was not lost.
- The final EAS and falsification fronts were restored and committed separately.
- Existing ADR-221/ADR-222 already contained the right direction: no positional
  stash identity and no speculative stash mutation.

## What Went Wrong

- The assistant called SO primitive/tool work “unrelated” instead of “a separate
  semantic front inside the SO.”
- The session used `stash@{n}` in explanations instead of the stash names and
  inspected file lists.
- Auto-checkpoint still had a legacy stash round-trip path before ADR-318.

## Corrective Actions

1. Adopt ADR-318: checkpoints are copy-only by default; stash is quarantine only.
2. Update `hooks/auto-checkpoint.sh` so default checkpointing copies dirty files
   into `.cognitive-os/checkpoints/` and does not touch `git stash`.
3. Update operator messages to require inspected/named targets before stash
   apply/drop.
4. Keep semantic fronts separated by commits/worktrees/branches whenever
   possible; use named stashes only as temporary quarantine.
5. Treat every new SO primitive/tool front as part of the SO even when isolated
   from the current commit.

## Preventive Rule

Do not say “restore `stash@{0}`” as an architectural instruction. Say:

```text
Review the named quarantine entry, confirm its file list, then apply or drop the
currently resolved ref for that exact entry.
```

For durable work, prefer a branch/worktree/commit. Stash is temporary quarantine,
not a source of truth.

## Verification

```bash
.venv/bin/python -m pytest tests/integration/test_auto_checkpoint_named_stash.py -q
bash -n hooks/auto-checkpoint.sh hooks/crash-recovery.sh hooks/stash-budget-warn.sh scripts/stash-leak-alarm.sh
.venv/bin/python -m py_compile lib/checkpoint_manager.py
```
