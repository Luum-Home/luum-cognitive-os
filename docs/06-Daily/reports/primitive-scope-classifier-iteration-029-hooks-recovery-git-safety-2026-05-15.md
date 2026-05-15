# Primitive SCOPE classifier — Iteration 029 hooks recovery/git safety

Date: 2026-05-15

## Goal

Reduce the 79 hook unknowns by reviewing a cohesive recovery/git/concurrent-edit safety subgroup.

## Manual classification decision

Kept these 17 hooks as `SCOPE: both` and added shared-surface evidence:

- `hooks/auto-checkpoint.sh`
- `hooks/auto-rollback-trigger.sh`
- `hooks/branch-ownership-lock.sh`
- `hooks/branch-ownership-release.sh`
- `hooks/crash-recovery.sh`
- `hooks/edit-lock-drain-parked.sh`
- `hooks/edit-lock-pre-tool.sh`
- `hooks/edit-lock-process-negotiations.sh`
- `hooks/edit-lock-session-end.sh`
- `hooks/post-agent-verify.sh`
- `hooks/post-git-orphan-notifier.sh`
- `hooks/pre-agent-snapshot.sh`
- `hooks/pre-commit-content-hash-dedupe.sh`
- `hooks/session-start-stash-reapply.sh`
- `hooks/session-start-worktree-nudge.sh`
- `hooks/symlink-mutation-guard.sh`
- `hooks/untracked-work-preservation-guard.sh`

## Evidence

These hooks enforce generic repository/agent-session safety:

- crash recovery and checkpoint/rollback safety;
- branch and edit locks for multi-agent sessions;
- subagent pre/post safety snapshots and TOUCH-scope verification;
- git orphan/duplicate-diff/worktree/stash protections;
- symlink and untracked-work preservation.

The behavior is useful while maintaining COS and while operating adopter repositories. COS paths are implementation/metrics details, not the value proposition.

## Classifier robustness update

Added exact/prefix semantic patterns for recurring shared safety families:

- `auto-checkpoint`, `auto-rollback-trigger`, `crash-recovery`;
- `branch-ownership*`, `edit-lock*`;
- `pre-agent-snapshot`, `post-agent-verify`;
- `post-git-orphan-notifier`, `pre-commit-content-hash-dedupe`;
- `session-start-stash-reapply`, `session-start-worktree-nudge`;
- `symlink-mutation-guard`, `untracked-work-preservation-guard`.

## Before / after

Before:

```json
{
  "total_unknown": 320,
  "hooks_unknown": 79
}
```

After:

```json
{
  "total_unknown": 303,
  "hooks_unknown": 62,
  "rules_unknown": 83,
  "scripts_unknown": 158
}
```
