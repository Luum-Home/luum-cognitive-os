<!-- SCOPE: both -->
---
name: worktree-triage
description: Triage a linked Git worktree against a target branch, port only unapplied work, validate, and remove the worktree only when clean and safe.
user-invocable: true
version: 1.0.0
last-updated: 2026-05-02
audience: both
tags: [git, worktree, coordination, safety, triage]
summary_line: "Compare a worktree to main and produce a safe port/validate/remove checklist."
platforms: ["codex", "claude-code", "generic-cli"]
prerequisites: ["git"]
routing_patterns:
  - pattern: '\bworktree[- ]?triage\b'
    confidence: 0.95
  - pattern: '\btriage\s+(linked\s+)?worktree\b'
    confidence: 0.85
  - pattern: '\bport\s+unapplied\s+work\b'
    confidence: 0.75
---

# Worktree Triage

Use this skill when a branch/worktree such as `bb5a` may contain useful work and
must be compared against `main` before cleanup.

The core rule is:

> Triage first; port only unapplied work; validate; commit/merge; remove the
> worktree only when the doctor says it is safe.

This skill is read-first. Do not delete, reset, stash-drop, or remove a worktree
until the checklist is green and the useful work is proven present on the target.

## When to invoke

- A linked worktree appears dirty, detached, or stale.
- An IDE shows changes in a worktree that may already be merged elsewhere.
- You need to clean up a worktree but must avoid losing work.
- A preserve/concurrent cleanup branch references a worktree path.
- Before running `git worktree remove` on any non-temporary worktree.

## Step 1: Identify target and worktree

Default target is `main`. Use the concrete worktree path shown by Git or the IDE.

```bash
git worktree list --porcelain
```

If the worktree is named or described as `bb5a`, resolve the full path from the
`worktree` lines.

## Step 2: Run the triage doctor

From the project root:

```bash
bash scripts/cos-worktree-triage.sh \
  --project-dir "$PWD" \
  --worktree /path/to/bb5a \
  --target main \
  --json
```

For human-readable output, omit `--json`.

The report includes:

- `already_applied_commits` — patch-equivalent work already on target;
- `commits_to_port` — commits whose patch is not on target;
- `blockers` — dirty files, conflicts, or stashes visible from the worktree;
- `safe_to_remove` — true only when there are no blockers and nothing left to port;
- `suggested_commands` — commands to inspect/port/validate/remove deliberately.

## Step 3: Port only unapplied work

If `commits_to_port` is non-empty, port only those commits or their relevant file
hunks. Prefer cherry-picking in order unless the report or conflicts show that a
manual selective patch is safer.

```bash
git switch main
git cherry-pick <sha-from-commits_to_port>
```

If a commit is listed under `already_applied_commits`, do not cherry-pick it just
because it exists in the worktree history.

## Step 4: Resolve blockers before cleanup

If the report contains `worktree-dirty`, inspect the worktree directly:

```bash
git -C /path/to/bb5a status --short --branch
git -C /path/to/bb5a diff --stat
```

If it contains `worktree-stashes-present`, inspect by ref. Do not use blind
`stash pop`:

```bash
git -C /path/to/bb5a stash list
git -C /path/to/bb5a stash show --name-status stash@{N}
```

Apply/drop only after you know whether the stash is duplicate, obsolete, or must
be ported.

## Step 5: Validate on target

Run the smallest trustworthy validation for the slice you ported. At minimum,
run the tests named by the touched area. For the triage primitive itself:

```bash
python3 -m pytest tests/behavior/test_cos_worktree_triage.py tests/behavior/test_cos_work_inventory.py -q
```

## Step 6: Re-run triage and remove only if safe

After porting and validation, re-run:

```bash
bash scripts/cos-worktree-triage.sh \
  --project-dir "$PWD" \
  --worktree /path/to/bb5a \
  --target main \
  --json
```

Only remove when:

- `commits_to_port` is empty;
- `blockers` is empty;
- `safe_to_remove` is `true`;
- validation passed;
- any commit/merge needed on target is complete.

Then:

```bash
git worktree remove /path/to/bb5a
```


## Related cleanup primitive

When the operator confirms there are no active agents and the remaining blockers
are only preserved stashes, temporary validation capsule worktrees, or zombie
session registry entries, switch to `preserved-wip-cleanup`. Do not use that
skill for named feature worktrees that still need porting; this skill remains
the required path for branch/worktree triage.

## Exit codes

- `0`: no blockers detected. Check `safe_to_remove` before cleanup.
- `2`: blockers exist; do not remove the worktree.

## Contextual Trigger

Keywords: worktree, linked worktree, bb5a, stale worktree, dirty worktree,
worktree cleanup, worktree remove, port work, cherry-pick only unapplied,
stash in worktree, safe to remove.
