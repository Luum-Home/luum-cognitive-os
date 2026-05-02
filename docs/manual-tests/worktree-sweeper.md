# Manual Test: Safe Worktree Sweeper

## Dry-run inventory

```bash
python3 scripts/cos-worktree-sweeper.py --dry-run --json
```

Expected:

- Main worktree is `keep`.
- Active validation capsules are `keep` when TTL has not elapsed or when active processes/open files are present.
- Stale detached temp worktrees with only `.venv` are `remove-candidate` after TTL.

## Apply on controlled temp prefix

```bash
python3 scripts/cos-worktree-sweeper.py \
  --dry-run \
  --ttl-seconds 0 \
  --no-default-safe-prefixes \
  --safe-prefix /private/tmp \
  --json
```

Confirm the only candidate is the intended stale worktree, then run:

```bash
python3 scripts/cos-worktree-sweeper.py \
  --apply \
  --ttl-seconds 0 \
  --no-default-safe-prefixes \
  --safe-prefix /private/tmp \
  --json
```

Expected:

- Apply reports `removed: true` for the intended path.
- `git worktree list --porcelain` no longer lists the path.
- The path no longer exists.

## Guards to verify before broad use

- Add a tracked modification in a temp worktree: decision must be `keep` with `tracked_changes`.
- Add `notes.txt` as untracked file: decision must be `keep` with `non_allowlisted_untracked`.
- Run a shell/process inside a temp worktree: decision must be `keep` with `active_process_or_open_file`.
- Use a branch worktree: decision must be `keep` with `branch_worktree`.
