---
type: quality-synthesis
source: docs/09-Quality/manual-tests/worktree-sweeper.md
provenance: "Proves the safe worktree sweeper correctly distinguishes removable stale temp worktrees from worktrees that must be kept due to tracked changes, untracked files, active processes, or branch use."
---

## What it is
A manual test for `scripts/cos_worktree_sweeper.py`, the tool that inventories and (optionally) removes stale git worktrees while guarding against accidental deletion of live work.

## Key mechanics
- **Dry-run inventory**: `cos_worktree_sweeper.py --dry-run --json` expects the main worktree marked `keep`; active validation capsules marked `keep` while TTL has not elapsed or active processes/open files exist; stale detached temp worktrees containing only `.venv` marked `remove-candidate` after TTL.
- **Apply on controlled temp prefix**: dry-run first with `--ttl-seconds 0 --no-default-safe-prefixes --safe-prefix /private/tmp --json` to confirm only the intended stale worktree is a candidate, then re-run with `--apply` and the same flags; expects `removed: true` for the intended path, the path absent from `git worktree list --porcelain`, and the path no longer existing on disk.
- **Guards to verify before broad use**: a tracked modification in a temp worktree forces `keep` with reason `tracked_changes`; an untracked `notes.txt` forces `keep` with `non_allowlisted_untracked`; a running shell/process inside the worktree forces `keep` with `active_process_or_open_file`; a branch worktree forces `keep` with `branch_worktree`.

## Relations & where used
Complements `validation-capsule.md` in guarding release-lane hygiene around temp worktrees; the sweeper's safe-prefix mechanism is the same pattern referenced by `branch-worktree-closure` skill guidance for deciding whether to merge, preserve, or remove worktrees.

## Status / caveats
No dated evidence block embedded — this is a repeatable procedure spec, not a logged historical run.
