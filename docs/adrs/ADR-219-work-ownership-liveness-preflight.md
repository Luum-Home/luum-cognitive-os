---
adr: 219
title: Work Ownership Liveness Preflight
status: accepted
implementation_status: implemented
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation/shipped/delivered evidence
---

# ADR-219: Work Ownership Liveness Preflight

## Status
Accepted


**Status**: Accepted  
**Date**: 2026-05-06  
**Related**: ADR-106, ADR-108, ADR-110, ADR-116, ADR-117, ADR-121, ADR-129, ADR-199, ADR-200, ADR-213

## Context

During the license-switch work, WIP was preserved to a temporary branch
`codex/stash-license-review-20260506`. That preservation prevented data loss,
but it did not prove the original producer had stopped working. A sibling
worktree still contained dirty copies of the same files and live processes had
that worktree as their current working directory.

The operator concern is broader than one branch: agents can truthfully say they
"preserved" or "completed" work while the observable repository state remains
split across stashes, linked worktrees, claims, stale locks, branches, and
running harness processes. Without a joined liveness view, later agents may
mistake archived evidence for completed work or mistake a safety stash for
trash.

## Decision

Cognitive OS will treat preserved branches as **evidence of a copy**, not proof
of inactivity. Before any agent claims closure, cleans stashes/worktrees, merges
a temporary branch, or reports that WIP is safe, it must be able to join the
following signals for the affected paths:

- current worktree dirty state;
- linked worktree dirty state;
- matching stashes;
- preserved/review branches (`codex/preserve-*`, `codex/stash-*`);
- task claims and expected file ownership;
- process activity with cwd/open files under linked worktrees.

The first executable surface is an extension to the existing work inventory
doctor instead of a new parallel tool:

```bash
scripts/cos_work_inventory.py --all --paths LICENSE NOTICE pyproject.toml --json
scripts/cos work ownership LICENSE NOTICE pyproject.toml
```

The output is conservative. A dirty linked worktree, active claim, matching
stash, or live process yields `active_or_unknown` or another
operator-review-required status. A branch-only copy yields
`preserved_copy_only`, explicitly warning that preservation does not prove the
original agent is inactive.

## Consequences

- Agents no longer have to infer ownership from one Git surface at a time.
- Temporary branches like `codex/stash-license-review-*` become first-class
  preservation evidence without becoming cleanup permission.
- Cleanup and closure workflows can fail closed when another worktree may still
  be active.
- Process activity remains a hint, not a proof: no open process does not mean a
  path is safe to delete.

## Alternatives rejected

- Trust the temporary branch — rejected because a preservation branch proves recoverability, not that the original worktree, stash, or agent is inactive.
- Drop all stale `auto-pre-agent-*` stashes after TTL — rejected as a complete answer because TTL cleanup cannot distinguish active linked worktrees, manual stashes, branch copies, and claims.
- Require humans to run separate Git/lsof commands — rejected because the failure mode is orchestration opacity; asking operators to compose `git stash`, `git worktree`, claims, locks, and `lsof` manually repeats the bug.

## Acceptance criteria

1. `scripts/cos_work_inventory.py --all --paths PATH --json` returns a
   `path_ownership` array with per-path status, matching dirty worktrees,
   matching stashes, matching claims, preserve branches, and operator action.
2. `scripts/cos work ownership PATH` routes to the same primitive.
3. A dirty linked worktree touching the requested path is classified as
   `active_or_unknown` and requires operator review.
4. A `codex/stash-*` preservation branch touching the requested path is reported
   as `preserved_copy_only`, not as proof of inactivity.
5. Unit tests cover linked-worktree and preservation-branch cases.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
