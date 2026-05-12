---

adr: 182
title: Branch Ownership Lock — Single-Writer Surface for Concurrent Orchestrators
status: accepted
implementation_status: implemented
date: 2026-05-05
supersedes: []
superseded_by: null
extends: []
implementation_files:
  - hooks/branch-ownership-lock.sh
  - lib/branch_lock.py
  - tests/contracts/test_branch_ownership_lock.py
  - .cognitive-os/runtime/branch-locks/
  - lib/session_coordination.py              # worktree intake companion
  - lib/agent_message_bus.py                 # auditor-to-operator companion
tier: maintainer
tags: [concurrency, worktree, governance, session-safety, postmortem-2026-05-05]
---
# ADR-182: Branch Ownership Lock — Single-Writer Surface for Concurrent Orchestrators

## Status

**Accepted.** Implemented as the ADR-182 branch-lock hook, library, CLI wrappers, and contract tests. Filed in response to the cross-session collision incident
documented in `docs/reports/postmortem-cross-session-collision-2026-05-05.md`.

## Context

The post-mortem identified that two concurrent orchestrator sessions can
hold the same git branch simultaneously without mutual visibility,
producing destructive race conditions (ADR-171 and ADR-179 in-flight
content was overwritten by tombstone files from a parallel session).

COS already has partial concurrency primitives:

- `.cognitive-os/runtime/task-claims.json` — advisory leases per-task,
  not per-branch.
- `.cognitive-os/sessions/active-sessions.json` — registry of active
  PIDs per worktree, not exclusion.
- `destructive-git-blocker.sh` — per-session, does not see peer
  sessions.
- ADR-111 concurrency_safety — passive (preserve_branches,
  stash_leak_alarm), not arbiter.

What is missing: a **hard exclusion lock** at the branch level that
blocks a second concurrent orchestrator from issuing destructive git
operations on a branch already held by another session.

## Decision

Introduce a **branch ownership lock primitive** with the following
contract:

### Lock acquisition

A session that intends to mutate a branch must acquire a lease before
operating. The lease is recorded under
`.cognitive-os/runtime/branch-locks/<branch-slug>.lock` and contains:

```json
{
  "branch": "session/41961ce2-paperclip-rejection-multi-surface",
  "session_id": "1778012502-40406-0062edf8",
  "pid": 40406,
  "worktree": "/Users/.../luum-agent-os",
  "acquired_at": "2026-05-05T17:00:00Z",
  "ttl_seconds": 14400,
  "expires_at": "2026-05-05T21:00:00Z",
  "renewed_at": "2026-05-05T19:30:00Z"
}
```

### Lock enforcement

A new `PreToolUse Bash` hook (`hooks/branch-ownership-lock.sh`) with
matcher targeting destructive git verbs (`commit`, `push`, `reset --hard`,
`rebase`, `merge`, `cherry-pick`, `stash apply`, `stash pop`,
`worktree add`, `worktree remove`, `branch -D`) checks the lock file
before allowing the operation.

Decision tree:

1. If no lock exists for the current branch: **acquire** the lock for
   this session, then proceed.
2. If the lock exists for the current session (or for a session whose
   PID is dead per `cos_session_registry.is_alive()` and the TTL has
   not been renewed): proceed.
3. If the lock exists for a different live session: **block**. Return a
   clear error message naming the holder and the time it acquired.

### Lock release

Lock is released:

- Explicitly when the orchestrator-LLM calls
  `bash scripts/cos-branch-release <branch>`.
- Implicitly on session-end (Stop hook).
- Implicitly when TTL expires AND the holder PID is no longer alive
  (zombie reaper).

### Auto-renewal

The lock holder's UserPromptSubmit hook auto-renews the TTL on every
prompt, keeping it alive for the lease window. A long idle session loses
the lease naturally.

### Worktree awareness

The lock key is the **branch name**, not the worktree. Two worktrees
checking out the same branch fight for the same lock. Different
branches in different worktrees do not contend.

### Auditor read-only carve-out

The branch lock protects writers, not auditors. An auditor agent may inspect
another worktree or branch without acquiring the branch writer lock, provided it
stays read-only and records the intake through the cross-session coordination
ledger.

Auditor flow:

1. Record worktree intake as `read-only`.
2. Inspect files, diffs, logs, tests, manifests, and ADRs.
3. Send findings to the operator/implementer through the directed agent message
   bus.
4. Do not patch, cherry-pick, revert, commit, or otherwise mutate the operator
   branch unless explicitly promoted to operator for that branch.

This avoids the failure mode where an auditor "helps" by importing another
worktree's policy into the active branch. The writer lock and the message bus
are complementary: the lock protects mutation boundaries; the message bus routes
read-only findings to the session that owns the mutation.

## Acceptance Criteria

1. `hooks/branch-ownership-lock.sh` exists, is registered in
   `scripts/_lib/settings-driver-claude-code.sh` as `PreToolUse Bash`
   matcher (after `destructive-git-blocker.sh`, before commit), and is
   in the security-profile registration markers.
2. `lib/branch_lock.py` exposes:
   - `acquire(branch: str, session_id: str, pid: int, worktree: Path, ttl_seconds: int = 14400) -> bool`
   - `release(branch: str, session_id: str) -> bool`
   - `holder(branch: str) -> dict | None`
   - `is_held_by_other(branch: str, session_id: str) -> bool`
   - `renew(branch: str, session_id: str) -> bool`
3. Tests: contract test verifies that a second session attempting
   `git commit` on a held branch is blocked with a non-zero exit and a
   clear stderr message; releases on session-end work correctly; TTL
   expiration with dead-PID releases the lock; renewal extends the TTL.
4. Operator override: env var `COS_ALLOW_BRANCH_OWNERSHIP_OVERRIDE=1`
   bypasses the block (analogous to existing `COS_ALLOW_DESTRUCTIVE_GIT`).
5. Lock files are git-ignored (`.cognitive-os/runtime/branch-locks/` is
   already inside the runtime ignore pattern).
6. Falsifiable claim (below) is testable.
7. Auditor read-only intake is documented and covered by the cross-session
   coordination/message-bus contracts; an auditor can emit a blocking finding
   without acquiring the operator branch lock.

## Border Cases

- **Operator runs `git commit` directly in a terminal outside any
  Claude Code session**: the hook does not run because PreToolUse only
  fires for Claude-tool-issued bash. The lock is advisory in this case.
  The post-mortem incident was Claude-internal, so this is acceptable
  for the immediate fix; broader enforcement would require a git pre-
  commit hook in `.git/hooks/`.
- **Single-session worktree creation that internally checks out a new
  branch**: the lock is acquired silently the first time a destructive
  git op fires on the new branch.
- **Session that legitimately needs to operate on multiple branches in
  sequence**: the orchestrator releases between branch switches.
- **Auditor reviewing a sibling worktree**: no writer lock is acquired if the
  auditor remains read-only; findings are sent through
  `scripts/cos-agent-message` and require acknowledgement by the target session
  when blocking.
- **Crashed session leaves a stale lock**: zombie reaper plus PID-alive
  check + TTL releases it within 5 minutes.

## Consequences

### Positive

- Tonight's incident becomes structurally impossible: the second
  session would have hit a hard block on its first commit attempt.
- Operator can confidently run multiple Claude Code tabs on different
  branches without fear of cross-talk.
- Post-mortem action item P1 is closed.

### Negative

- Adds latency (~10 ms) to every destructive git operation.
- Requires a new hook in the standard security profile, increasing
  surface area.
- A misbehaving zombie reaper could leave a session blocked. Mitigation:
  TTL-based auto-release plus explicit operator override.

### Neutral

- This is a per-machine local lock; it does not coordinate across
  machines. Cross-machine concurrency is out of scope here and would be
  addressed by the manager-of-managers daemon (ADR-184).

## Alternatives rejected

- **`flock` on `.git/refs/heads/<branch>`**: too coarse, would block
  read-only `git status`. Rejected.
- **Git pre-commit hook**: works for one machine but does not see
  Claude-side intent (e.g. about-to-cherry-pick). Rejected as primary;
  may be a complementary layer.
- **Cooperative protocol via Engram MCP**: relies on agents being
  well-behaved. Tonight proved that assumption is false. Rejected.

## Falsifiable Claim

The lock is correct if, in a controlled test, two simultaneously-started
Claude Code sessions both targeting the same branch produce: (a) the
first session acquiring the lock, (b) the second session's `git commit`
hook failing with the documented error, (c) after first session
releases or TTL expires, the second session can proceed.

If under any plausible workload the lock fails open (lets both sessions
commit), the implementation is broken and ADR-182 must be revisited.

## Cross-References

- `docs/reports/postmortem-cross-session-collision-2026-05-05.md` —
  origin incident.
- `docs/reports/session-state-forensics-2026-05-05.md` — forensic
  detail.
- ADR-088 commit_provenance — complementary post-hoc audit.
- ADR-111 concurrency_safety — passive primitives this ADR makes
  active.
- ADR-183 cross-session event log — companion (this ADR
  prevents conflicts; ADR-183 surfaces awareness of peers).
- ADR-184 manager-of-managers daemon — supersedes this lock when daemon
  is the only writer, but ADR-182 is operative until then.
- `docs/architecture/cross-session-coordination-ledger.md` — worktree intake
  and intent claims.
- `docs/architecture/agent-message-bus.md` — auditor-to-operator directed
  findings and acknowledgement.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

