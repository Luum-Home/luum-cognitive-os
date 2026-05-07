# Git State Cleanup — 20260506T220040Z

**Date**: 2026-05-06
**Mode**: archive-first cleanup
**Base**: main @ 979dab14

## Branches

| Branch | SHA | Decision | Evidence | Archive ref |
|---|---:|---|---|---|
| `codex/stash-license-review-20260506` | `ced6dd48598109053e7465c4f5c3277fa8a3c493` | delete local branch; not merged textually | `git cherry -v main codex/stash-license-review-20260506` marks commit as already patch-equivalent to main; patch-id equals `598b95bd` | `refs/archive/branches/20260506T220040Z/codex-stash-license-review-20260506` |

## Stashes

| Stash SHA | Subject | Decision | Evidence | Archive ref | Patch file |
|---:|---|---|---|---|---|
| `4ed170ecb0fccf82fe28c8ab84aca8bda45dbda4` | `On claude/priceless-thompson-bbabce: auto-pre-agent-toolu_01PTqvdqNni5hbEiTdjtE9u8` | drop from `refs/stash` after archive | patch-id equals `598b95bd` license switch already in main | `refs/archive/stashes/20260506T220040Z/0-On-claude-priceless-thompson-bbabce-auto-pre-agent-toolu_01PTqvdqNni5hbEiTdjtE9u` | `.cognitive-os/recovery/git-cleanup-20260506T220040Z/stash-0-4ed170ecb0fc.patch` |
| `1967522e35727434505814e1060a3a375aa28b20` | `On claude/priceless-thompson-bbabce: auto-pre-agent-toolu_01SYoc2d8fhjtesuie3NAZQM` | drop from `refs/stash` after archive | patch-id equals `598b95bd` license switch already in main | `refs/archive/stashes/20260506T220040Z/1-On-claude-priceless-thompson-bbabce-auto-pre-agent-toolu_01SYoc2d8fhjtesuie3NAZQ` | `.cognitive-os/recovery/git-cleanup-20260506T220040Z/stash-1-1967522e3572.patch` |
| `3c14beaeac9408ea710b9766a82f2174d97edda0` | `On claude/priceless-thompson-bbabce: auto-pre-agent-toolu_01PMVAmLX2fyQqHZYTzJ4J6D` | drop from `refs/stash` after archive | patch-id equals `598b95bd` license switch already in main | `refs/archive/stashes/20260506T220040Z/2-On-claude-priceless-thompson-bbabce-auto-pre-agent-toolu_01PMVAmLX2fyQqHZYTzJ4J6` | `.cognitive-os/recovery/git-cleanup-20260506T220040Z/stash-2-3c14beaeac94.patch` |

## Worktrees

Only the primary `main` worktree was present at cleanup time. `git worktree prune` was still run to clear stale metadata.

## Recovery

- Branch recovery: `git branch codex/stash-license-review-20260506 <archive-ref>`.
- Stash recovery: each stash object is preserved under `refs/archive/stashes/<stamp>/...` and each patch is copied under `.cognitive-os/recovery/git-cleanup-<stamp>/`.
- These archive refs are intentionally local; do not push them to a public remote without a history/privacy review.

## Final verification

```text
git branch -vv                  # only main remains
git worktree list --porcelain   # only primary main worktree remains
git stash list                  # empty
```

A first scripted drop loop used an unquoted `stash@{0}` form and did not remove entries under the active shell expansion rules; the final cleanup used quoted `git stash drop 'stash@{0}'` repeatedly until `git stash list` was empty.
