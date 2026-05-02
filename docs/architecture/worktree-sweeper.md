# Safe Worktree Sweeper

## Purpose

The safe worktree sweeper removes stale temporary git worktrees only when the OS can prove they are safe to remove. The importable Python implementation is `scripts/cos_worktree_sweeper.py`; the optional operator shell entrypoint is `scripts/cos-worktree-sweeper.sh`.

## Commands

```bash
python3 scripts/cos_worktree_sweeper.py --dry-run --json
python3 scripts/cos_worktree_sweeper.py --apply --ttl-hours 2 --json

# Equivalent human-facing shell wrapper:
bash scripts/cos-worktree-sweeper.sh --dry-run --json
```

Naming contract: Python scripts stay snake_case; hyphenated human commands are Bash wrappers only.

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
python3 scripts/cos_worktree_sweeper.py \
  --dry-run \
  --ttl-seconds 0 \
  --no-default-safe-prefixes \
  --safe-prefix /private/tmp \
  --json

python3 scripts/cos_worktree_sweeper.py \
  --apply \
  --ttl-seconds 0 \
  --no-default-safe-prefixes \
  --safe-prefix /private/tmp \
  --json
```

The second command should be used only after the dry-run shows exactly the intended candidate.
