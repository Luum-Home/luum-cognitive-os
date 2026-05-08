# Runbook: cos-cleanup

Tiered cleanup of the recurring stale artifacts that accumulate during agent
work: orphan `.git/index.lock`, week-old validation capsules, expired
ADR-116 task-claim locks, dead session pointers, merged
`worktree-agent-*`/`feat/cos-*` branches, orphan worktrees, and zombie
`cos_executor.py --daemon` processes.

The script is intentionally tiered so the safe class can be automated and the
destructive class always requires explicit operator intent.

## When to run each tier

| Tier | Cadence | Risk | Default? |
| --- | --- | --- | --- |
| 1 | Hourly / SessionEnd / pre-commit | none — only stale files | `--dry-run` |
| 2 | End of sprint, branch hygiene day | medium — deletes refs/worktrees | confirmed `--apply` |
| 3 | Manual, with operator present | destructive — touches WIP/live procs | `--aggressive --apply` |

Default invocation is `--tier=1 --dry-run`: zero risk, prints a plan.

## What each tier removes

### Tier 1 (auto, low-risk)
- `.git/index.lock` when no `git` process is alive **and** mtime > 5 min.
- `/tmp/luum-agent-os-*` and `/private/tmp/luum-agent-os-*` validation capsules
  with mtime > 7 days.
- ADR-116 task-claim locks under `.cognitive-os/runtime/**.json` whose
  `expires_at` < now.
- `.cognitive-os/sessions/.current-session-*` pointers whose session id is no
  longer present in any running process.

### Tier 2 (semi-auto, medium-risk; operator-confirmed)
- Local branches matching `worktree-agent-*`, `codex/agent/task-desc-*`, or
  `feat/cos-*` where `git rev-list --count <branch> ^main == 0` (already merged
  or empty). Deleted with `git branch -d` (safe — refuses if unmerged).
- Worktrees registered in `git worktree list` whose branch was deleted (orphan).
  Pruned with `git worktree remove --force`.
- `cos_executor.py --daemon` processes whose `--working-dir` no longer exists.

In `--dry-run` the script prints the plan. In `--apply` it prompts `[y/N]`
per category. Set `COS_CLEANUP_NONINTERACTIVE=1` for unattended runs.

### Tier 3 (destructive, requires `--aggressive --apply`)
- Branches with **unmerged** commits relative to `main` are **listed only** —
  never auto-deleted. The audit log emits a hint: rebase or cherry-pick first.
- Worktrees with uncommitted WIP — `git stash push -u` or bail. Stash entries
  are tagged `cos-cleanup-stash-<epoch>`.
- Live `cos_executor.py --daemon` processes — SIGTERM with a 10 s grace
  period. **Never** escalates to SIGKILL.

## Recovery

- **Branch deleted accidentally**: `git reflog` for the SHA, then
  `git branch <name> <sha>`.
- **Worktree pruned**: re-add with `git worktree add <path> <branch>`. The
  filesystem path was destroyed by `worktree remove --force`; recover from
  backup or recreate from the branch tip.
- **WIP stashed**: `git stash list | grep cos-cleanup-stash` then
  `git stash apply <ref>`.
- **Daemon SIGTERM'd**: relaunch via the same orchestrator command.

## Audit log

Every candidate (dry-run) and every applied action are appended to
`.cognitive-os/cleanup-audit.jsonl` (one JSON object per line):

```json
{"ts":"2026-05-08T12:00:00Z","tier":1,"action":"rm-file","target":"/path","reason":"stale git index lock (age=420s)","dry_run":false,"applied":true,"result":"ok","error":null}
```

Override location with `COS_CLEANUP_AUDIT_LOG=<path>` (used in tests).

## Race with spawning agents — gotcha

`cos-cleanup` enumerates state, then mutates. An agent that **spawns between
those two phases** can:

1. Have its task-claim lock deleted while it is still running (cleanup read
   `expires_at` from a slightly stale snapshot). Mitigation: tier 1 only
   targets locks with `expires_at < now` — so the agent must have already
   leaked its lock for cleanup to act. Live agents holding valid leases are
   never affected.
2. Have its session pointer removed in the window between the pgrep check and
   `rm -f`. Mitigation: pointers are recreated on next session start; the only
   cost is one extra start-up write.

For fleets with high spawn rate, run cleanup at SessionEnd or quiesce points,
not mid-sprint.

## CI / automation

- `scripts/cos-cleanup.sh --tier=1 --apply` is safe in CI (tier-1 is
  conservative). Set `COS_CLEANUP_NONINTERACTIVE=1` to skip prompts (no-op at
  tier 1, required for tier 2).
- Exit code semantics: `0` success, `1` tier-3 candidate exists (review needed),
  `2` usage error.
- The optional `hooks/session-end-cleanup.sh` runs `--tier=1 --apply`
  quietly. It is **not** registered in `settings.json` by default.
