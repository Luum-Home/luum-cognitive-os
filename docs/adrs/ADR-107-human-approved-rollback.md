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

## Acceptance Criteria

1. The trigger never prints that rollback will execute automatically.
2. Tests cover all phases with approval-required behavior.
3. Contract tests prevent automatic destructive execution language from returning.
4. The destructive git blocker continues proving `git revert` is blocked by default.
