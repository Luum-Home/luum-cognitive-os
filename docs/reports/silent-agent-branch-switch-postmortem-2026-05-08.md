---
title: Post-Mortem — Silent Agent Branch Switch and Unexpected Commit Destination
date: 2026-05-08
status: accepted
scope: maintainer
severity: MEDIUM
tags: [postmortem, git-safety, branch-governance, agentic-primitives, codex]
incident_window: '2026-05-08 03:28–03:38 America/Argentina/Buenos_Aires'
author: Codex under operator review
---

# Post-Mortem — Silent Agent Branch Switch and Unexpected Commit Destination

## Severity classification

**MEDIUM.** No committed work was lost, and the feature branch was eventually
merged back to `main`. The failure was procedural and architectural: an agent
changed branch context in the background, committed on
`fix/c4-portability-test-failures`, then the operator discovered the mismatch
after the fact. That violates the branch-as-contract model used by the
multi-agent safety layer.

## Incident summary

The operator asked whether it was acceptable that a commit landed on
`fix/c4-portability-test-failures` because an agent changed branch in the
background. The immediate verdict was: the final state may be recoverable, but
silent branch switches are unacceptable by default. Branch identity determines
where future commits land, which PR will be opened, which locks apply, and how
work is audited.

Local reflog evidence shows the sequence:

| Local time | Reflog event |
|---|---|
| 2026-05-08 03:28:53 | `checkout: moving from main to fix/c4-portability-test-failures` |
| 2026-05-08 03:35:04 | `commit: fix(tests): disable auto-rebase in ancestry-gate failure proof` |
| 2026-05-08 03:36:13 | `commit: feat(readiness): close M2/M3/M4 — asciicast driver + engram topic-key audit + sanitize smoke` |
| 2026-05-08 03:37:05 | `commit: feat(readiness): rescue agent outputs (H3 license res + M1 release signing + C4 fixes)` |
| 2026-05-08 03:38:48 | `checkout: moving from fix/c4-portability-test-failures to main` |
| 2026-05-08 03:38:48 | `merge fix/c4-portability-test-failures` |

Current `main` contains merge commit `3fd5f82c` for that branch, so the incident
is not an unresolved data-loss event. It is a gap in branch-change prevention
and operator visibility.

## Impact

- Commits temporarily landed on a branch the operator did not expect.
- The operator had to reconstruct state with `git reflog`, `git log`, and
  branch inspection instead of receiving a pre-change receipt.
- Existing branch locks did not help because the lock primitive protects writes
  on the **current** branch; it did not treat branch switching itself as a
  mutating operation requiring approval.
- Existing destructive-git protections blocked resets, path checkouts, rebases,
  force-pushes, and protected-branch commits, but allowed branch context changes
  such as `git switch` and `git checkout <branch>`.

## Root cause analysis

### Primary root cause — branch switch was not a governed git mutation

`hooks/destructive-git-blocker.sh` handled many destructive git operations, but
its interception vocabulary did not include branch context changes. Before this
post-mortem, the blocked set included `git reset`, `git checkout -- <path>`,
`git restore`, `git rebase`, `git worktree` mutations, `git branch -D`,
force-pushes, and protected `main`/`master` writes. It did **not** block:

- `git switch <branch>`
- `git switch -c <branch>`
- `git checkout <branch>`
- `git checkout -b <branch>`

Those commands are not always destructive to file contents, but they are
control-plane mutations: they change where subsequent commits land. For agents,
that requires the same explicitness as a destructive mutation.

### Secondary root cause — branch ownership lock starts too late

`hooks/branch-ownership-lock.sh` acquires/enforces a lock only when a destructive
write-like operation is about to run (`commit`, `push`, `merge`, `rebase`,
`cherry-pick`, reset/stash/worktree/force-delete variants). It derives the
branch from `git branch --show-current` at hook time. If a previous command
silently switched branches, the lock faithfully protects the **new** branch.
It cannot prove the switch was authorized.

### Tertiary root cause — branch-per-task policy is prelaunch/advisory for this path

ADR-225's branch-per-task primitive checks declared task IDs against expected
branch names, and strict mode exists for write/cloud/detached lanes. The incident
path was a raw shell git transition inside an already-running session, not a new
write-agent prelaunch. Therefore the branch-per-task policy never had a chance
to block the context switch.

### Contributing factor — session branch helper intentionally supports switching

`scripts/cos-session-branch.sh --switch` is valid when an operator explicitly
wants an isolated branch. The helper is not the problem; the missing guard was
that equivalent raw git branch switches could occur without an auditable
operator acknowledgement.

## Corrective actions implemented

### 1. Block branch context changes by default

`hooks/destructive-git-blocker.sh` now classifies branch switches as
`branch_context_change` and blocks them by default:

- `git switch <branch>`
- `git switch -c <branch>`
- `git checkout <branch>`
- `git checkout -b <branch>`

The block message explains that silent switches make commits land on unexpected
branches.

### 2. Add explicit branch-switch override

A legitimate branch switch remains possible, but it must be intentional and
audited:

- inline: append `--allow-branch-switch`
- environment: `COS_ALLOW_BRANCH_SWITCH=1`

The override is logged to `.cognitive-os/metrics/git-op-blocks.jsonl` with
`reason=branch_switch_override`.

### 3. Preserve existing destructive-git behavior

The older `git checkout -- <path>` handling remains classified as destructive
working-tree discard. Force-push, protected branch writes, WIP rebase guard, and
other destructive-git policies remain unchanged.

### 4. Reinforce tests

`tests/unit/test_destructive_git_block.py` now covers:

- blocking `git switch <branch>`
- blocking `git switch -c <branch>`
- blocking `git checkout <branch>`
- blocking `git checkout -b <branch>`
- auditing inline branch-switch override
- auditing environment branch-switch override

Focused validation passed:

```text
python3 -m pytest tests/unit/test_destructive_git_block.py -q
85 passed
```

## Preventive policy

Agents may create or switch branches only when one of the following is true:

1. The operator explicitly requested it.
2. The agent announces the branch transition before acting, including previous
   branch, target branch, reason, and expected commit destination.
3. The command uses an explicit audited override (`--allow-branch-switch` or
   `COS_ALLOW_BRANCH_SWITCH=1`).
4. A higher-level COS primitive such as `scripts/cos-session-branch.sh --switch`
   is used in a context where the operator already asked for a session branch.

Silent branch changes are treated as governance violations even if no file data
is lost.

## Acceptance criteria

1. `git switch fix/c4-portability-test-failures` through the Bash hook exits
   non-zero and mentions branch context.
2. `git checkout fix/c4-portability-test-failures` through the Bash hook exits
   non-zero and mentions branch context.
3. `git switch fix/c4-portability-test-failures --allow-branch-switch` exits 0
   and logs `reason=branch_switch_override`.
4. Existing destructive-git blocker tests still pass.
5. This post-mortem is linked from `docs/README.md`.

## Follow-up recommendations

- ADR-239 converts the incident response into an accepted architecture decision: `isolated_worktree` is the default for write agents, and `main_worktree` is legacy single-agent mode.
- Consider a git native `pre-commit` companion that rejects commits when the
  branch changed after session start without a COS receipt. The current hook
  protects tool-mediated Bash commands, not arbitrary external terminals.
- Add branch-switch receipts to any future TUI or daemon operation that changes
  branch context.
- Keep ADR-225 prelaunch enforcement and this Bash-layer branch switch guard as
  complementary controls: prelaunch protects declared task lanes; Bash guard
  protects mid-session context drift.
