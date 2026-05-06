# Post-Mortem — State Retention Self-Bite and Retention Controller — 2026-05-06

## Summary

ADR-116 correctly blocked agent launches when stale Git stash state could hide
unrecovered WIP. The failure was operational: Cognitive OS had created safety
state eagerly (`auto-pre-agent-*` stashes, task claims, agent bus folders) but
had not cleaned mature safety state automatically. The result was a self-bite:
the safety system blocked later work on its own residue.

## Impact

- Parallel agent launches were blocked by stale stash findings.
- Hook output repeated large JSON payloads instead of one compact operator
  summary.
- Follow-up audit showed additional accumulation: terminal task claims and
  hundreds of agent-bus directories.

## Root Cause

Cognitive OS had a preservation-first default but no maturity model for cleanup.
The system treated all state as equally risky to mutate, so safe terminal state
and auto-generated artifacts accumulated until preflight surfaced them as risk.

## What Went Well

- ADR-116 prevented silent WIP loss.
- ADR-199 introduced a manifest and archive-first cleanup path.
- `cos stash cleanup --execute` removed only auto-pre-agent stashes and did not
  touch manual `wip-matrix-merge`.
- Manual WIP was later archived explicitly with a preserved ref and patch before
  being removed from the stash stack.

## What Went Wrong

- The first implementation was mostly manual/advisory. It did not repair before
  the preflight blocker that users actually hit.
- Session-end audit was dry-run, so terminal claims and agent bus directories
  remained above their retention budget until manually executed.
- Preflight output was not compact enough for repeated parallel launch failures.

## Corrective Action

Introduce a conservative State Retention Controller:

- `observe`: inventory only, never mutate.
- `repair-safe`: archive-first automatic cleanup for mature terminal state.
- `repair-before-block`: preflight may repair once before blocking if and only if
  the blocker is a known auto-generated artifact.

The first automatic set is intentionally narrow:

- `task-claims-ledger`: compact terminal records.
- `agent-bus-directories`: archive stale/overflow directories.
- `auto-pre-agent-stashes`: archive-first cleanup only when preflight would
  block solely on auto-pre-agent residue.

Manual stashes, preserve worktrees, runtime locks, and metrics rotation remain
`observe` until separately proven.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. Manual/session stashes are never selected by automatic preflight repair.
2. Stale auto-pre-agent stashes are archived and removed before preflight blocks.
3. Session-end auto-safe cleanup archives/compacts only repair-safe surfaces.
4. Repeated runs are idempotent and cooldown/lock bounded.
5. Preflight failure output is compact and actionable.
```
