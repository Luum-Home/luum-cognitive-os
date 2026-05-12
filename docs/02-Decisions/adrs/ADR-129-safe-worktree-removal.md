---

adr: 129
title: Safe Worktree Removal — No Silent rm -rf Fallback
status: accepted
implementation_status: implemented
date: 2026-05-02
supersedes: []
superseded_by: null
implementation_files:
  - hooks/_lib/safe-worktree-remove.sh
  - hooks/validation-lock-cleanup.sh
  - hooks/_lib/execute-repair.sh
  - scripts/cos-validation-capsule.sh
  - scripts/cos-validation-break.sh
tier: core
tags: [worktree, safety, data-loss, hooks]
---

# ADR-129: Safe Worktree Removal — No Silent rm -rf Fallback

## Status

Accepted. Implemented in commit `d5ecda43` with the shared
`hooks/_lib/safe-worktree-remove.sh` helper and adopted by the four destructive
worktree-removal callsites.

## Context

Four code paths in this repository remove git worktrees with the same
unsafe pattern:

```bash
git worktree remove --force "$PATH" 2>/dev/null || rm -rf "$PATH"
```

Callsites:

1. `hooks/validation-lock-cleanup.sh:137` — SessionStart hook that cleans
   stale validation-capsule locks. Has 4-layer staleness gates upstream
   (TTL, PID liveness, heartbeat, activity), so the destructive op rarely
   fires; but if the gates ever miss, the antipattern bypasses any safety.
2. `scripts/cos-validation-capsule.sh:113` — `EXIT/INT/TERM` trap for a
   validation-capsule process. Runs on every capsule shutdown.
3. `scripts/cos-validation-break.sh:145` — user-invoked "break the lock"
   command. Already destructive by design, but should still surface why
   git refused.
4. `hooks/_lib/execute-repair.sh:116` — auto-repair path cleanup. Same
   pattern with a slightly different ordering (`rm -rf` then prune).

All four share three problems:

- **`2>/dev/null` on the git command** swallows the reason `git worktree
  remove` refused. Common reasons (worktree in use, lockfile present,
  filesystem permission) are all legitimate signals that the directory
  should NOT be deleted right now.
- **`rm -rf` as fallback** ignores the signal and deletes anyway. If git
  refused because another process is actively writing to the worktree,
  `rm -rf` removes that process's working tree out from under it.
- **No audit trail.** When a worktree disappears unexpectedly, there is
  nowhere to go to find out which callsite removed it or why git's safety
  check was bypassed.

The DX assessment (`docs/06-Daily/reports/dx-assessment-2026-05-02.md`) classified
ADR-128 items as "data integrity (recoverable)". This concern is in a
different category: **destruction of in-progress work, not recoverable**.
Hence a separate, narrower ADR.

## Decision

Introduce a single shared helper, `hooks/_lib/safe-worktree-remove.sh`,
that all four callsites use instead of inlining the unsafe pattern.

The helper:

1. Captures stderr from `git worktree remove --force` rather than
   discarding it.
2. On success — logs one JSONL line with `action: "removed"`, the path,
   the caller label, and a UTC timestamp. Returns 0.
3. On failure — logs one JSONL line with `action: "remove_failed"`,
   the path, the caller label, the captured stderr, and a UTC timestamp.
   Then runs `git worktree prune` (a non-destructive op that only clears
   dangling worktree registrations from `.git/worktrees/`). **Does not
   `rm -rf`.** Returns the original git exit code.
4. Caller decides what to do with a failed removal — typically: leave
   the directory on disk for human triage. A stranded worktree is a
   recoverable problem; a deleted in-progress worktree is not.

Audit log: `.cognitive-os/metrics/worktree-removals.jsonl`, consistent
with the existing metrics directory convention.

The helper accepts a `COS_WORKTREE_REMOVE_ALLOW_RM_RF=1` escape hatch
for documented one-shot recovery scenarios. Default is off. The hatch
is logged distinctly (`action: "force_rm_rf"`) so its use is visible
in the audit trail.

## Acceptance Criteria

1. `git grep -nE 'git worktree remove --force.*\\|\\| rm -rf'` returns
   zero results in the source tree (excluding this ADR and the audit
   log).
2. Calling the helper with a non-existent path returns 0 silently
   (idempotent).
3. Calling the helper against a worktree that git refuses to remove
   (simulated by holding a file open) leaves the directory on disk
   and writes a `remove_failed` entry to the audit log.
4. Calling the helper successfully writes a `removed` entry to the
   audit log including the caller label.
5. `COS_WORKTREE_REMOVE_ALLOW_RM_RF=1` makes the helper fall back to
   `rm -rf` AND writes a `force_rm_rf` entry. Default-off behaviour
   verified by absence of the env var in the four callsites.

## Evidence

- Control-plane command: `scripts/cos-boring-reliability --profile core --json`
- Validation command: `python3 -m pytest tests/unit/test_safe_worktree_remove.py -q`
- Implementation proof: commit `d5ecda43` replaced silent `rm -rf` fallbacks
  with `hooks/_lib/safe-worktree-remove.sh` and writes
  `.cognitive-os/metrics/worktree-removals.jsonl`.
- Tier rationale: `tier: core` is justified because this is a default safety
  invariant against unrecoverable WIP deletion, not a maintainer-only metric or
  lab governance experiment.

## Border Cases

- **Validation capsule trap on process exit.** The `cos-validation-capsule.sh`
  cleanup trap runs when the capsule's owning process is exiting. If
  git refuses, leaving the directory means the next staleness sweep
  will find it on disk without a corresponding lock and clean it up
  via `validation-lock-cleanup.sh`. No action lost.
- **Auto-repair path.** `execute-repair.sh` cleans worktrees it
  created itself; if git refuses, the leftover worktree blocks the
  next auto-repair on the same branch. The retry will surface a
  visible failure (instead of a silent overwrite) and the human gets
  a chance to inspect.
- **`cos-validation-break.sh` invoked manually.** The user is asking
  for the lock to be broken. If git refuses, the helper logs the
  reason and the user can re-run with the explicit
  `COS_WORKTREE_REMOVE_ALLOW_RM_RF=1` after confirming nothing is
  actively writing.
- **Symlinked worktree paths.** The helper uses the path as given;
  it does not resolve symlinks. If a callsite passes a symlink, that
  is the callsite's responsibility (matches existing behaviour).
- **Concurrent invocations.** No shared lockfile is used. Two
  concurrent calls against the same path produce two audit entries;
  one will succeed, the other will hit the "not a worktree" git
  error and log accordingly. Acceptable.

## Consequences

**Positive.**

- A worktree that another process is actively using is no longer
  silently destroyed.
- Every removal — successful or not — is traceable in
  `worktree-removals.jsonl`. When a worktree goes missing, there is
  one place to look.
- Failures surface stderr from git, which is usually self-explanatory
  ("worktree contains modified or untracked files", "is locked", etc.).

**Negative.**

- Validation capsule directories may accumulate on disk if git refuses
  to remove them. Mitigation: existing staleness sweep
  (`validation-lock-cleanup.sh`) runs on every SessionStart and will
  re-attempt; persistently stranded worktrees are surfaced in the
  audit log.
- One additional helper file in `hooks/_lib/` to maintain.
- Behaviour change for callers that relied on `rm -rf` succeeding when
  git refused. We accept this — the previous behaviour was the bug.

## Cross-references

- Source: `docs/06-Daily/reports/dx-assessment-2026-05-02.md` (raised in
  follow-up conversation, 2026-05-02).
- Related: ADR-128 (data-layer integrity), ADR-117 (stash mutation
  reversibility — same family of "no silent destructive ops").
- Companion log: `.cognitive-os/metrics/worktree-removals.jsonl`.

## Alternatives rejected

- Leave the ADR without an alternatives section — rejected because ADR-067+ audit contracts require a falsifiable record of considered options.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

