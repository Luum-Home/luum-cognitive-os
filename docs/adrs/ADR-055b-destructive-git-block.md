---
adr: 55b
title: Destructive Git Op Block (User Context Elevation)
status: accepted
implementation_status: partial
date: '2026-04-21'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
---

# ADR-055b — Destructive Git Op Block (User Context Elevation)

**Status**: Accepted
**Date**: 2026-04-21
**Supersedes**: partial warn-only behavior of `hooks/destructive-git-blocker.sh`
  for user/orchestrator context (previously documented as "warn-only by design"
  in `docs/reports/bug2-reset-cascade-forensics-2026-04-20.md §5`).
**Relates to**: ADR-003 (Agent Git Safety, Mechanism C), ADR-055a (reserved),
  r5-stash-residue (work-queue parked item — closed by this ADR).

## Context

`hooks/destructive-git-blocker.sh` (ADR-003 Mechanism C) blocks destructive
git operations when the invocation originates from a sub-agent
(`CLAUDE_AGENT_ID` set). In user/orchestrator context it previously emitted a
WARN on stderr but allowed the command to proceed (exit 0).

The forensic report for bug2 (reset-cascade) documented a residual risk R5
("stash-residue reuse from user context") and marked it parked because it was
"not actionable without product decision on restricting user-context
destructive git ops; warn-only by design."

The product decision (decision #6, this ADR) is now made: **block by default in
user context too, with explicit override mechanisms.**

### Why warn-only was insufficient

- Stash-residue pattern (user's own `git stash pop` executed parallel to
  auto-pre-agent stashes) can pop the wrong entry and re-enact the exact
  incident class Mechanism C was built to prevent.
- Warning output is easy to miss when mixed into terminal noise, especially
  during active orchestration.
- The warn-only posture meant the OS "knew" the op was dangerous but still
  executed it — a trust-erosion pattern documented in `rules/trust-score.md`.

## Decision

### 1. Elevate user-context to BLOCK (exit 2)

Destructive git ops in user context now fail with exit code 2 and a clear
rationale printed to stderr. The previous exit-0-with-warn behavior is removed.

Agent context retains exit code 1 for backwards-compat with existing tests and
ADR-003 Mechanism C invariants.

### 2. Expanded destructive-op coverage

New ops added to the block list:

| Op                  | Rationale                                              |
|---------------------|--------------------------------------------------------|
| `git branch -D`     | Force-deletes branches with unmerged commits           |
| `git rebase --abort`| Discards in-progress rebase state; partial work lost   |

Existing ops (unchanged): `git stash pop/drop/apply`, `git reset --hard`,
`git checkout --` (incl. `checkout HEAD -- <path>`), `git clean -f[dx]`,
`git restore`, `git revert`, `git worktree`.

### 3. Override mechanisms (two, layered)

| Override             | Scope           | Use case                                     |
|----------------------|-----------------|----------------------------------------------|
| `--allow-destructive` inline flag | Per-command    | One-off intentional destructive op           |
| `COS_ALLOW_DESTRUCTIVE_GIT=1` env | Session-wide   | Known cleanup session (e.g. resolving rebase)|

Only literal `"1"` activates the env override. `"true"`, `"yes"`, non-empty
truthy strings do NOT unlock — this is deliberate to prevent typo-level
accidental bypass.

The inline flag is recognized as a whole token anywhere in the command:
`git reset --hard HEAD~1 --allow-destructive` works, as does
`git --allow-destructive reset --hard HEAD~1`.

### 4. Bypass contexts (SO-internal, not user-initiated)

Three bypass contexts allow destructive ops without override:

| Condition                   | Rationale                                                  |
|-----------------------------|------------------------------------------------------------|
| `CI=1` or `CI=true`         | CI runners reset working state for isolation               |
| `PYTEST_CURRENT_TEST` set   | Test teardown may reset fixtures                           |
| `COS_GIT_BYPASS=1`          | Reaper, watchdog, and sandbox-sample operations            |

**Critical invariant**: bypass contexts do NOT apply when `CLAUDE_AGENT_ID`
(or any agent-context signal) is set. An agent running under pytest/CI is
still blocked — the bypass exists for SO infrastructure, not for agent work
that happens to run in a test harness.

### 5. Audit log

Every decision (block, override, bypass) is appended to
`.cognitive-os/metrics/git-op-blocks.jsonl` with `event` in
`{blocked, override, bypassed}` and context fields (`reason`, `context`,
`agent_id`, `op`, `command`).

## Consequences

### Positive

- r5-stash-residue is closed (previously parked).
- User-context destructive ops can no longer happen by reflex or in a
  distracted terminal session without an explicit acknowledgment.
- Override mechanisms are discoverable (error message lists them both) and
  cheap to invoke when legitimately needed.
- Audit trail preserved — every override is logged with a reason.

### Negative / Tradeoffs

- Interactive users who routinely use `git reset --hard` will need to either
  export `COS_ALLOW_DESTRUCTIVE_GIT=1` once per session or learn the
  `--allow-destructive` suffix. This is friction by design.
- The `--allow-destructive` flag is not recognized by git itself and will be
  passed through to git — users must ensure they remove it OR git will error
  out (which is a separate, safe failure mode). Mitigation: the override is
  primarily meant for the env variant; the flag is for one-offs.
- CI/pytest bypass relies on environment variables that an attacker with
  local shell access could set. This is acceptable: an attacker with local
  shell access already has git access directly.

### Kill-switch interaction

The hook sources `_lib/killswitch_check.sh` at line 31 (per ADR-028 §584).
If the killswitch is flipped, the blocker early-exits. This is an orthogonal
override that does NOT require changes here — R3 in the forensic report
already documents the killswitch-as-blanket-bypass risk.

## Verification

- Unit tests: `tests/unit/test_destructive_git_block.py` (35 tests, all pass)
- Behavior tests: `tests/behavior/test_destructive_git_blocker.py` (17 tests,
  all pass — `TestUserContext` updated to assert exit 2)
- Chaos tests: `tests/chaos/test_reset_cascade_detector.py`,
  `tests/chaos/test_safety_drill.py` (17 tests, all pass — user-context test
  updated to assert block)

Total: 69 tests passing across unit + behavior + chaos layers.

## Rollback

If this elevation causes operational pain, rollback is:
1. Revert `hooks/destructive-git-blocker.sh` to the previous commit.
2. Delete `tests/unit/test_destructive_git_block.py`.
3. Restore the old `test_blocker_sh_warns_but_allows_in_user_context` test body.
4. Re-open `r5-stash-residue` in `.cognitive-os/work-queue.json`.

No state migration is required — the metrics log schema accepts the old and
new event types interchangeably.
