# Safe Worktree Sweeper

## Purpose

`cos-worktree-sweeper` removes stale temporary git worktrees only when the OS can prove they are safe to remove.

## Commands

```bash
python3 scripts/cos-worktree-sweeper.py --dry-run --json
python3 scripts/cos-worktree-sweeper.py --apply --ttl-hours 2 --json
```

The importable implementation is:

```bash
python3 scripts/cos_worktree_sweeper.py --dry-run --json
```

## Candidate requirements

| Gate | Required state |
|---|---|
| Main worktree | Not the primary repository worktree |
| Git state | Detached HEAD |
| Safe prefix | Path under an allowed temporary prefix |
| TTL | Directory age older than configured TTL |
| Process use | No process/open file references the path |
| Tracked files | No modified/staged/deleted tracked files |
| Untracked files | Only allowlisted untracked paths such as `.venv` |

## Defaults

Safe prefixes:

- `/tmp`
- `/private/tmp`
- `$TMPDIR` when available

Allowlisted untracked paths:

- `.venv`

## Manual cleanup example

For a known stale laptop worktree:

```bash
python3 scripts/cos-worktree-sweeper.py \
  --dry-run \
  --ttl-seconds 0 \
  --no-default-safe-prefixes \
  --safe-prefix /private/tmp \
  --json

python3 scripts/cos-worktree-sweeper.py \
  --apply \
  --ttl-seconds 0 \
  --no-default-safe-prefixes \
  --safe-prefix /private/tmp \
  --json
```

The second command should be used only after the dry-run shows exactly the intended candidate.
