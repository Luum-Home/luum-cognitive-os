---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/cos-cleanup.md
provenance: "Explains the tiered cos-cleanup runbook so operators know which risk tier to run when, what each tier removes, how to recover from an over-aggressive run, and the race condition to watch for with actively spawning agents."
---

## What it is

A runbook for the tiered cleanup script that removes recurring stale artifacts from agent work — orphan git locks, old validation capsules, expired task-claim locks, dead session pointers, merged branches/worktrees, and zombie daemon processes — designed so the safe class can be automated while the destructive class always requires explicit operator intent.

## Key mechanics

- **Three tiers by risk**: Tier 1 (none — stale files only; cadence hourly/SessionEnd/pre-commit; default `--dry-run`), Tier 2 (medium — deletes refs/worktrees; cadence end-of-sprint; requires confirmed `--apply`), Tier 3 (destructive — touches WIP/live processes; manual, operator-present only; requires `--aggressive --apply`). Default invocation is `--tier=1 --dry-run` (zero risk, prints a plan).
- **Tier 1 removes**: stale `.git/index.lock` (no live git process AND mtime >5 min), `/tmp` and `/private/tmp` `luum-agent-os-*` validation capsules >7 days old, expired ADR-116 task-claim locks, and orphaned `.current-session-*` pointers.
- **Tier 2 removes**: merged/empty local branches matching `worktree-agent-*`, `codex/agent/task-desc-*`, or `feat/cos-*` (via safe `git branch -d`, which refuses unmerged branches), orphaned worktrees (`git worktree remove --force`), and daemon processes whose working dir no longer exists. Prompts `[y/N]` per category in `--apply` mode unless `COS_CLEANUP_NONINTERACTIVE=1`.
- **Tier 3 is deliberately non-destructive by default even at this tier**: branches with unmerged commits are LISTED ONLY, never auto-deleted (hint to rebase/cherry-pick first); worktrees with uncommitted WIP get `git stash push -u` (tagged `cos-cleanup-stash-<epoch>`) or the operation bails; live daemons get SIGTERM with a 10s grace period and explicitly never escalate to SIGKILL.
- **Recovery paths documented per category**: accidentally deleted branch → `git reflog` + `git branch <name> <sha>`; pruned worktree → re-add via `git worktree add` (filesystem path is unrecoverable, must restore from backup or recreate from branch tip); stashed WIP → `git stash list | grep cos-cleanup-stash` then `git stash apply <ref>`; SIGTERM'd daemon → relaunch via the same orchestrator command.
- **Audit log**: every dry-run candidate and every applied action append a JSON line to `.cognitive-os/cleanup-audit.jsonl` (overridable via `COS_CLEANUP_AUDIT_LOG`).
- **Race condition with spawning agents**: cleanup enumerates state then mutates in two separate phases, so an agent spawning in that window can have its task-claim lock deleted (mitigated: only expired locks are targeted, so this requires the agent to have already leaked its lock) or its session pointer removed mid-window (mitigated: pointers are recreated on next session start, costing only one extra write). Recommendation: run cleanup at SessionEnd or quiesce points, not mid-sprint, for high-spawn-rate fleets.
- **CI/automation**: `scripts/cos-cleanup.sh --tier=1 --apply` is safe in CI. Exit codes: 0 success, 1 tier-3 candidate exists (review needed), 2 usage error. An optional `hooks/session-end-cleanup.sh` runs tier-1 quietly but is explicitly NOT registered in `settings.json` by default.

## Relations & where used

References ADR-116 (task-claim lock semantics) for tier-1 lock expiry logic. The optional `hooks/session-end-cleanup.sh` hook is documented as available but not wired by default.

## Status / caveats

No dated point-in-time claims — this is a stable operational runbook. No internal inconsistencies found; the tier boundaries (what counts as "safe" vs "destructive") are consistently applied throughout.
