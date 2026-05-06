<!-- SCOPE: both -->
---
name: preserved-wip-cleanup
description: Archive-first cleanup for preserved WIP stashes, temporary validation capsule worktrees, and zombie session registry entries after all agents stop.
user-invocable: true
version: 1.0.0
last-updated: 2026-05-02
audience: both
tags: [git, cleanup, stashes, worktrees, coordination, safety]
summary_line: "Backup preserved WIP, remove temporary blockers, and prove the inventory is clean."
platforms: ["codex", "claude-code", "generic-cli"]
prerequisites: ["git", "python3"]
routing_patterns:
  - pattern: '\bpreserved[- ]?wip[- ]?cleanup\b'
    confidence: 0.95
  - pattern: '\bcleanup\s+(wip|stash)\b'
    confidence: 0.85
  - pattern: '\bzombie\s+session\b'
    confidence: 0.75
---

# Preserved WIP Cleanup

Use this skill only after the operator confirms no agents or IDEs are still
working in the repository. The workflow turns the manual cleanup protocol into a
repeatable primitive: backup first, then remove only explicit cleanup classes,
then prove the inventory is clean.

## Safety contract

- Dry-run by default.
- Destructive actions require `--apply` and an explicit cleanup selector.
- Stashes are backed up before `git stash clear` using patch files and local
  `refs/cos-backup/stashes/<cleanup-id>/...` refs.
- Temporary validation capsule worktrees are backed up with status, diff, and
  untracked tarball before `git worktree remove --force`.
- Active validation capsule worktrees are kept. A capsule is active when the
  source repo lock points to it with a live PID/fresh heartbeat, or when a
  process/open file is detected under the capsule path.
- Zombie session registry cleanup keeps live PIDs and removes only dead PIDs.
- Never use this skill to remove a named feature worktree; use
  `worktree-triage` for non-temporary worktrees.

## Step 1: Confirm current blockers

```bash
python3 scripts/cos_work_inventory.py --all --strict --json
```

Inspect summary fields: `blockers`, `stash_count`, `worktree_count`,
`worktree_stash_count`, and `race_risk_count`.

## Step 2: Dry-run cleanup

```bash
python3 scripts/cos_cleanup_preserved_wip.py \
  --repo "$PWD" \
  --all \
  --json
```

This creates a timestamped backup directory but does not drop stashes, remove
worktrees, or rewrite the registry.

## Step 3: Apply only after confirmation

```bash
python3 scripts/cos_cleanup_preserved_wip.py \
  --repo "$PWD" \
  --all \
  --apply \
  --json
```

Use narrower selectors when needed:

```bash
python3 scripts/cos_cleanup_preserved_wip.py --repo "$PWD" --drop-stashes --apply
python3 scripts/cos_cleanup_preserved_wip.py --repo "$PWD" --remove-validation-capsules --apply
python3 scripts/cos_cleanup_preserved_wip.py --repo "$PWD" --clean-zombie-registry --apply
```

## Step 4: Verify clean inventory

```bash
python3 scripts/cos_work_inventory.py --all --strict --json
```

Expected closure state for a fully cleaned repo:

- `blockers = 0`
- `stash_count = 0`
- `worktree_count = 1`
- `worktree_stash_count = 0`
- `race_risk_count = 0`

## Recovery

The cleanup report prints `backup_dir`. To inspect backed-up stashes:

```bash
ls "$backup_dir/stashes"
git for-each-ref "refs/cos-backup/stashes/$(basename "$backup_dir")"
```

To restore manually, create a branch from a backup ref or apply a patch from the
backup directory. Do not restore blindly into `main`; use a session branch.

## Contextual Trigger

Keywords: clean preserved WIP, cleanup stashes, drop stashes safely, validation
capsule cleanup, zombie sessions, blockers zero, worktree stash count, no agents
working, cerrar sesión limpia, limpiar todo.
