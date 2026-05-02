<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Rollback Planning Protocol

## Purpose

When the SDD verify-apply loop exhausts all retries, capture the failure and produce a rollback evidence package. ADR-107 supersedes the previous immediate rollback execution behavior: every destructive git operation requires explicit human approval in every project phase.

## Trigger

Rollback planning activates when `sdd-verify` fails with critical issues, retry count reaches `max_retries`, or the orchestrator reports: "Verify-apply loop exceeded 3 retries". The hook requests a rollback plan and does not run git mutation commands.

## Phase-Aware Behavior

| Phase | Behavior |
|-------|----------|
| `reconstruction` | PLAN REQUIRED — human approval before destructive git |
| `stabilization` | PLAN REQUIRED — human approval before destructive git |
| `production` | HALT/PLAN REQUIRED — human approval before destructive git |
| `maintenance` | HALT/PLAN REQUIRED — human approval before destructive git |

## Required Evidence

Before any rollback command is approved, produce change identity, exact candidate commits, concurrency check, dirty worktree status, affected files, proposed commands, verification commands, and abort conditions.

## Safety Boundaries

Rollback planning NEVER executes `git revert` automatically, runs `git restore`, `git reset --hard`, `git clean`, stash mutation, branch deletion, or worktree mutation automatically, modifies main/master directly, runs database rollbacks, changes secrets, or bypasses `hooks/destructive-git-blocker.sh`.

## Monitoring

Events are logged with `mode=plan_required`, `approval_required=true`, and `destructive_commands_executed=false`.

## Contextual Trigger

This rule is loaded when: rollback, revert, verify failure, retry exhaustion, sdd-verify fail.
