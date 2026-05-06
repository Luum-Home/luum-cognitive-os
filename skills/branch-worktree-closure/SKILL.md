<!-- SCOPE: both -->
---
name: branch-worktree-closure
description: Use when an agent finds leftover codex/* or claude/* branches, extra git worktrees, or open feature worktrees and must decide whether to merge, preserve, or remove them safely.
user-invocable: true
version: 1.0.0
last-updated: 2026-05-02
audience: both
tags: [git, worktrees, branches, merge-queue, coordination, cleanup]
summary_line: "Close leftover agent branches/worktrees without losing work or bypassing main landing gates."
platforms: ["codex", "claude-code", "generic-cli"]
prerequisites: ["git", "python3"]
routing_patterns:
  - pattern: '\bbranch[- ]?worktree[- ]?closure\b'
    confidence: 0.95
  - pattern: '\b(leftover|cleanup)\s+(codex|claude)\b'
    confidence: 0.8
  - pattern: '\b(merge|preserve|remove)\s+worktrees?\b'
    confidence: 0.75
---

# Branch / Worktree Closure

Use this skill whenever a repo has an unexpected `codex/*`, `claude/*`, or
other agent branch/worktree left open. Do not delete first. Classify first.

## Closure protocol

### 1. Inventory the current state

```bash
git status --short --branch
git branch --list 'codex/*' 'claude/*' -vv
git worktree list --porcelain
python3 scripts/cos_work_inventory.py --all --strict --json
```

Record for each extra branch/worktree:

- path;
- branch;
- dirty status;
- commits ahead of `main`;
- commits behind `main`;
- stashes in that worktree;
- whether the diff is already present in `main`.

### 2. Classify

| State | Action |
|---|---|
| Dirty worktree or stash exists | Stop and preserve first. Use `preserved-wip-cleanup` only after operator confirmation. |
| Branch fully merged into `main` and worktree clean | Remove the worktree, then delete the branch. |
| Branch has useful commits not in `main` | Rebase onto `origin/main`, validate, land via `scripts/merge-to-main.sh`, then delete. |
| Branch is obsolete/duplicate and clean | Confirm duplicate evidence (`git diff main..branch` empty or patch already in main), then delete. |
| Unsure | Produce a short closure report and ask the operator; never force-delete. |

### 3. Rebase useful work

```bash
git -C "$WORKTREE" fetch origin main
git -C "$WORKTREE" rebase origin/main
```

If conflicts appear, stop. Do not resolve by discarding work unless the operator
explicitly approves.

### 4. Validate proportionally

Choose the smallest trustworthy test lane for the files changed. Examples:

```bash
git -C "$WORKTREE" diff --name-status main..HEAD
python3 -m pytest tests/behavior/test_cos_cleanup_preserved_wip.py -q
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

If tests fail because the target does not exist, find the current test name;
do not silently treat that as success.

### 5. Land through the single-writer path

Never push directly from `main`. From the session branch/worktree:

```bash
bash scripts/merge-to-main.sh --validate '<targeted validation command>'
```

This fast-forwards `main`, pushes, and records the queue event.

### 6. Close the branch/worktree only after ancestry proves it landed

```bash
git merge-base --is-ancestor "$BRANCH" main
git worktree remove "$WORKTREE"
git branch -d "$BRANCH"
git status --short --branch
python3 scripts/cos_work_inventory.py --all --strict --json
```

Expected closure:

- target branch is gone;
- target worktree is gone;
- `main...origin/main` is clean;
- `blockers = 0`;
- `stash_count = 0`;
- `worktree_stash_count = 0`.

## Report format

```text
BRANCH_WORKTREE_CLOSURE
branch: <name>
worktree: <path>
classification: merged | useful-landed | preserved | duplicate | blocked
validation: <commands + result>
landing: <commit/push result or why not>
cleanup: <worktree/branch removal result>
remaining_risk: <none or explicit risk>
```

## Contextual Trigger

Keywords: leftover codex branch, leftover claude worktree, branch abierta,
worktree abierto, cleanup branch, close worktree, merge leftover branch,
foundation hardening branch, codex/* branch, claude/* branch, cerrar rama,
cerrar worktree.
