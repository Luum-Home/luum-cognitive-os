# Post-Mortem — Hidden WIP in Auto Pre-Agent Stash

**Date**: 2026-05-06  
**Severity**: P1 operator-trust / data-preservation  
**Status**: Fixed by ADR-213 hook-order invariant

## Summary

License-switch WIP appeared to be missing from progressive commits. It was not
lost. It had been moved into two duplicate `auto-pre-agent-*` stashes by the
pre-agent snapshot path before a later Agent launch preflight blocked.

Because the Agent tool never launched, the normal PostToolUse restore path did
not fire. The result was a hidden-WIP failure: COS preserved the work, but made
it invisible to the operator and to normal `git status`.

## Impact

- Operator could not see expected progressive commits for the license switch.
- The working tree looked clean even though meaningful product/legal WIP existed
  in stash.
- Subsequent stale-stash guards correctly blocked/raised warnings, but the root
  cause was earlier: stash mutation happened before launch admission finished.

## Timeline

1. License switch files were modified in the working tree.
2. A later Agent launch began.
3. `pre-agent-snapshot.sh` ran and created an `auto-pre-agent-*` stash.
4. `agent-prelaunch.sh` / governed preflight blocked the Agent launch.
5. Since Agent never launched, PostToolUse restore did not run.
6. The WIP remained only in stash until manual forensics archived and preserved
   it on `codex/stash-license-review-20260506`.

## Root cause

Hook order was wrong in Claude settings/security profiles:

```text
pre-agent-snapshot.sh  # mutates stash
agent-prelaunch.sh     # may block launch
```

Mutation-before-admission violates the data-preservation boundary. A hook that
can hide WIP must not run before a hook that can still cancel the operation
without a guaranteed restore phase.

## Fix

ADR-213 changes the invariant:

```text
agent-prelaunch.sh     # blocking launch admission
pre-agent-snapshot.sh  # stash/copy snapshot only after launch is admitted
```

Changed surfaces:

- `.claude/settings.json`
- `templates/security-profiles/standard.json`
- `templates/security-profiles/paranoid.json`
- `scripts/_lib/settings-driver-claude-code.sh`
- `hooks/pre-agent-snapshot.sh` documentation
- `tests/unit/test_agent_hook_order.py`

## Non-fix explicitly rejected

Do not solve this by making stash cleanup more aggressive. The problem is not
that stale auto-pre-agent stashes exist; the problem is that a blocked launch
created them before restore was possible.

## Preventive rule

Any hook that mutates stash, hides WIP, deletes files, or rewrites working-tree
state must run only after all blocking admission gates have passed, unless it
also has explicit restore-on-block semantics.

## Regression tests

Added `tests/behavior/test_agent_blocked_preflight_no_stash.py` to reproduce the
incident class end-to-end in a temporary git repo:

1. create a manual stash that makes `agent-prelaunch.sh` block;
2. create visible dirty operator WIP;
3. run the active Agent hook window from `.claude/settings.json`;
4. assert the preflight blocks before snapshot, no `auto-pre-agent-*` stash is
   created, and the WIP remains visible in `git diff`;
5. run a control with the old bad order and prove it would hide WIP in an
   `auto-pre-agent-*` stash.
