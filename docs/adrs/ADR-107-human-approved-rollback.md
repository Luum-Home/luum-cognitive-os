# ADR-107 — Human-Approved Rollback Boundary

<!-- SCOPE: both -->

**Status**: Accepted
**Date**: 2026-05-02
**Author**: Maintainer

## Status

Accepted. This ADR supersedes the previous phase-aware behavior that allowed immediate rollback execution in `reconstruction` and `stabilization`.

## Context

The original auto-rollback primitive allowed automatic execution in low-risk phases and included broad `git revert --no-edit HEAD~N..HEAD` guidance. That is unsafe in multi-session workflows because HEAD ranges can include concurrent work and hooks cannot prove commit ownership.

## Decision

The trigger hook MUST NOT execute `git revert`, `git restore`, `git reset`, `git clean`, `git checkout --`, stash mutation, branch deletion, or worktree mutation. Every project phase requires human approval before destructive git operations. The trigger emits a rollback plan request and logs `mode=plan_required`, `approval_required=true`, and `destructive_commands_executed=false`.

## Consequences

### Positive

- Rollback guidance becomes safe in concurrent sessions because hooks no longer mutate shared git state.
- Operators receive an explicit plan request with the approval boundary and audit fields.

### Negative

- Recovery takes one human approval step longer than the previous automatic rollback behavior.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep phase-aware automatic rollback | Unsafe because HEAD ranges can include concurrent work from other agents. |
| Allow automatic rollback only in reconstruction | Still unsafe; reconstruction is exactly where concurrent WIP is most likely. |
| Use stash-based rollback | Stashes hide ownership and were already part of the multi-agent confusion pattern. |

## Verification

```bash
python3 -m pytest tests/unit/test_auto_rollback_trigger.py -q
python3 -m pytest tests/behavior/test_destructive_git_blocker.py -q
```

## Acceptance Criteria

1. The trigger never prints that rollback will execute automatically.
2. Tests cover all phases with approval-required behavior.
3. Contract tests prevent automatic destructive execution language from returning.
4. The destructive git blocker continues proving `git revert` is blocked by default.
