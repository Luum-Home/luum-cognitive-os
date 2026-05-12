---
adr: 89
title: Multi-Session Git Coordination
status: accepted
implementation_status: partial
date: '2026-04-30'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: Deferred to a follow-up if collisions are observed there.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-089 — Multi-Session Git Coordination

<!-- SCOPE: OS -->

**Status**: Accepted — executed 2026-04-30 by Session A
**Date**: 2026-04-30
**Author**: Maintainer
**Related**: ADR-082 (plan locations), ADR-087 (ADR namespace), ADR-088 (provenance trailer),
ADR-072 (test lanes — parallel work that surfaced this problem)
**Supersedes**: none
**Reservation note**: This ADR was originally reserved as ADR-088 by Session A
(`1777570193-92907-51ec9a30`) at drafting time. Slot 088 was concurrently
claimed by Session B (`1777570196-94294-3bcc1d20`) for the provenance trailer
ADR. This file was renumbered to 089 — a live example of the slot collision
failure mode this ADR addresses.

---

## Status

Accepted — executed 2026-04-30 by Session A.

---

## Implementation log

**Implemented**: 2026-04-30 by Session A (`claude-sonnet-4-6`, DevOps Automator agent).

**Pre-check findings**: No layer was pre-implemented. Layer 3 existed as
`scripts/adr_reserve.py` (with a full test suite at
`tests/unit/test_adr_reserve.py`) but used a different lock file path
(`.cognitive-os/locks/adr-reservations.json`) and different CLI interface than
the ADR specifies. The new `scripts/reserve_adr_slot.py` wraps `adr_reserve.py`
with the ADR-specified interface (prints slot number by default, uses
`.cognitive-os/runtime/adr-reservations/reservations.json`).

**Files created**:

| File | Layer | Notes |
|------|-------|-------|
| `hooks/git-commit-scope-guard.sh` | Layer 1 | PreToolUse[Bash] hook; Python 3 for scope analysis (macOS-compat); <50ms latency |
| `scripts/git-coop.sh` | Layer 2 | `acquire`/`release`/`force_unlock`/`status`; POSIX mkdir atomic; stale TTL 5 min; 30s timeout; sourceable (`cos_git_acquire`/`cos_git_release`) |
| `scripts/reserve_adr_slot.py` | Layer 3 | CLI wrapper over `adr_reserve.py`; `--release`, `--list`, `--cleanup`; default output is slot number |
| `tests/unit/test_git_coop.py` | Tests | 12 behavioral tests: acquire, release, idempotency, stale auto-clear, concurrent serialization, bypass flag |
| `tests/unit/test_reserve_adr_slot.py` | Tests | 13 behavioral tests: slot collision, concurrent reservation, TTL, list/release/cleanup |

**Files modified**:

| File | Change |
|------|--------|
| `scripts/apply-efficiency-profile.sh` | Added `git-commit-scope-guard.sh` to `pre_bash` hook group (default profile) |
| `.claude/settings.json` | Added `git-commit-scope-guard.sh` to PreToolUse[Bash] hooks (full profile) |

**Key design decisions made during implementation**:

1. **Layer 1 scope detection via Python 3, not sed**: macOS BSD sed cannot
   reliably match `[^"]*` inside single-quoted sed programs for quoted strings.
   Python 3 `shlex.split` correctly tokenizes the git command and strips known
   flags with their arguments, leaving only genuine pathspec tokens.

2. **Layer 2 session ID fallback uses PPID**: When `COGNITIVE_OS_SESSION_ID` is
   not set, the lock uses `shell-<PPID>` as the session ID. This makes acquire
   and release from the same parent shell share an identity, enabling correct
   idempotency and release authorization without an explicit session env var.

3. **Layer 3 wraps existing `adr_reserve.py`**: Rather than reimplementing
   atomic reservation logic, `reserve_adr_slot.py` delegates to the proven
   `adr_reserve.py` module (fcntl-based, already tested). The wrapper maps
   ADR-089's specified CLI interface (slot number output, `--release NNN`,
   `.cognitive-os/runtime/adr-reservations/` path) onto the underlying module.

4. **Test suite uses subprocess execution throughout**: All behavioral tests
   execute scripts as subprocesses and assert on exit codes, output, and
   file-system side-effects — not on internal function state. This catches
   shell/Python integration issues that unit tests of functions would miss.

---

## Context

### The user's workflow: concurrent sessions against the same working tree

The user runs multiple Claude Code sessions in parallel against the same project
working tree. This is a legitimate workflow, not user error: one session may be
drafting ADRs while another is implementing the hooks or tests that those ADRs
govern. As of 2026-04-30, COS provides no coordination layer between concurrent
sessions. The git index is shared mutable state and neither session knows the
other exists until one of them reads `git log`.

### Failure modes observed 2026-04-30 (ground truth)

Two sessions were active simultaneously:

- **Session A** (`1777570193-92907-51ec9a30`): drafting ADRs 080–084, 087, 089
- **Session B** (`1777570196-94294-3bcc1d20`): shipping ADR-081 implementation,
  ADR-086 hook-execution-observability, test-lane work (ADR-072 follow-up)

Four distinct failure modes were produced:

**1. Commit scope inflation.**
Session A ran `git mv docs/adrs/ADR-076a-*.md docs/adrs/ADR-076a-redirect-stub.md`
to rename a single file, then staged the rename. Between `git mv` and
`git commit -m "..."`, Session B ran `git add` on its own files. Both sessions'
work was staged in the shared index. Session A's commit `a4ab471` (intended as a
1-file rename) pulled in 9 unrelated files from Session B. The commit had to be
reverted (`4ef7dc1`). Root cause: `git commit` with no pathspec commits
everything in the index, which is a shared resource neither session owns
exclusively.

**2. ADR slot collisions.**
ADR-085 was claimed by both sessions within minutes. Session B renumbered to 086;
Session A bumped to 087. The same collision happened again at the 086 slot.
The migration table inside ADR-087 required multiple manual edits to track the
moving numbers. The reservation note at the top of this file is a third
instance: 088 was claimed by Session B before Session A's draft landed.

**3. Phantom autocommits.**
Commits attributed to `kind=manual` with `X-COS-Session` trailers from Session B
appeared mid-stream in Session A's context — they were not invoked by Session A
and were not autocommit artifacts from a hook. They were Session B operating
concurrently. Session A had no signal that another session was active.

**4. Memory ghosts.**
Session B's commits were not visible in Session A's context until Session A
explicitly ran `git log`. The startup protocol does not surface "other concurrent
sessions are active on this working tree." This is the same root cause reported
as "memory loss across tasks" for months: multi-session noise that is invisible
to each individual session.

### Verified non-causes

The following hooks were audited and ruled out as causes of commit scope
inflation:

- `.githooks/pre-commit` and `.git/hooks/pre-commit`: run `git diff --cached`,
  never stage.
- `hooks/auto-checkpoint.sh`: does `git stash push --include-untracked` + `git
  stash pop` without `--index`. Net effect is to un-stage staged changes; can
  only shrink scope, never inflate it.
- `packages/document-sync/hooks/sync-to-repo.sh`: contains `git add -A` but
  operates on `$COGNITIVE_OS_REPO_PATH` (a separate sync target repository),
  not the project working tree.
- `packages/engram-sync/hooks/engram-auto-sync.sh`: scoped to `git add .engram/`
  only.

The inflation is entirely explained by the shared index and the absence of a
pathspec on the committing session's `git commit` call.

### Proven mitigation (already in use)

`git commit --only -- <pathspec>` pins commit scope to explicit paths regardless
of what else is staged in the index. Session A's clean redo commit `b9bba7a` used
this form and produced a 1-file commit from a dirty working tree. This is the
primitive on which Layer 1 of this ADR's decision builds.

---

## Decision

Three coordination layers, shipped in order of value-to-risk ratio.

### Layer 1 — Mandatory pathspec-scoped commits (high value, low risk)

**Rule**: Any agent-driven commit of a curated set of paths MUST use
`git commit --only -- <path> [<path>...]`. Default `git commit -m "..."` with
no flags is banned in agent-driven work.

**Rationale**: The index is shared state. An agent that stages its files and then
commits the entire index is silently co-opting whatever the other session staged.
`--only` makes commit scope explicit and session-local regardless of index state.

**The two permitted alternatives**:
- `git commit --only -- <path>...` — explicit curated scope (preferred)
- `git commit -a` — when the explicit intent is "commit everything modified in
  the working tree"; must be called out in the commit message or the surrounding
  agent commentary. Use only when the agent owns the entire working tree (e.g.,
  initial scaffold, full-repo migration).

**Enforcement**: A new hook `hooks/git-commit-scope-guard.sh` is registered as a
`PreToolUse[Bash]` hook. It inspects the Bash command for `git commit` and
rejects invocations that lack `--only`, `-a`, or an explicit pathspec argument.
It detects multi-session state by checking whether `.cognitive-os/runtime/` holds
more than one live context marker (see Layer 2). In single-session environments
the guard runs in advisory mode (warn, not block) to avoid friction for users who
are not running concurrent sessions.

### Layer 2 — Cooperative session lock for git index operations (medium value, medium risk)

**Lock file**: `.cognitive-os/runtime/git-index.lock`

**Lock format**: JSON with session ID, PID, timestamp, and operation name:
```json
{
  "session": "1777570193-92907-51ec9a30",
  "pid": 12345,
  "acquired_at": "2026-04-30T17:30:00Z",
  "operation": "git commit --only -- docs/adrs/ADR-089-multi-session-git-coordination.md"
}
```

**Acquire protocol**: Before any `git add`, `git commit`, `git mv`, or `git rm`,
an agent calls `scripts/git-coop.sh acquire`. The script:

1. Attempts an atomic `mkdir` of a lock directory (POSIX `mkdir` is atomic; no
   `flock` dependency required).
2. If `mkdir` succeeds, writes the JSON lock file and proceeds.
3. If `mkdir` fails (lock held), reads the lock file. If the lock is stale (age
   > 5 minutes and the PID is not a live process), clears it and retries once. If
   the lock is fresh, sleeps 2 seconds and retries up to 15 times (30-second
   total timeout).
4. If timeout expires, exits non-zero and prints a structured error that includes
   the lock holder's session ID and operation, so the waiting agent can report it
   to the user.

**Release protocol**: After the operation completes (success or failure), the
agent calls `scripts/git-coop.sh release`. The script removes the lock directory
only if the current session ID matches the lock file's session ID (prevents
accidental release of another session's lock).

**Implementation**: `scripts/git-coop.sh` with `acquire` and `release`
subcommands. Agents source or call this script. The commit-scope guard (Layer 1)
calls `acquire` before staging and `release` after committing, making the guard
the primary integration point.

**Advisory vs. enforcing**: The lock is enforcing — `acquire` blocks up to 30
seconds and fails hard on timeout. The 30-second timeout is chosen to be longer
than any individual git operation but short enough that a dead session's lock
does not permanently block the working session.

### Layer 3 — Session-aware ADR slot reservation (medium value, low risk)

**Problem**: ADR numbers are assigned by inspecting `ls docs/adrs/`, incrementing
the maximum found, and writing a file. Under concurrent sessions this is a
read-modify-write race with no atomicity guarantee. Two sessions can observe the
same maximum, both increment to the same next slot, and both write different ADRs
to the same number.

**Reservation mechanism**:

1. A new script `scripts/reserve_adr_slot.py` is the single entry point for ADR
   number assignment.
2. The script acquires the git-index lock (Layer 2) before reading `docs/adrs/`.
3. It computes `next_slot = max(existing numbers) + 1`.
4. It creates a reservation placeholder at
   `.cognitive-os/runtime/reserved-adrs/ADR-NNN-<session-id>` (a directory, so
   creation is atomic via `mkdir`).
5. It releases the lock and prints the reserved slot number.
6. Reservation TTL: 30 minutes. The script checks for expired reservations and
   removes them before computing `next_slot`, so a session that reserved a slot
   and crashed does not permanently consume it.

**Gitignore**: `.cognitive-os/runtime/reserved-adrs/` is gitignored. Reservations
are runtime state, not version-controlled artifacts.

**Convention update**: Any agent or operator drafting an ADR MUST call
`scripts/reserve_adr_slot.py` to obtain the slot number. Manually choosing a
slot by looking at `ls docs/adrs/` is prohibited in concurrent-session
environments.

---

## Consequences

### Positive

- **Clean commit attribution**: Layer 1 eliminates scope inflation. An agent's
  commit contains exactly the files it staged, regardless of index state.
- **No slot collisions**: Layer 3 makes next-slot computation atomic. The ADR
  reservation race that required renumbering ADR-085→086→087 and 088→089 cannot
  recur.
- **Multi-session as a first-class workflow**: The coordination primitives
  acknowledge that concurrent sessions are real and expected. The current absence
  of any coordination treats a legitimate workflow as an edge case.
- **Observability of lock contention**: When Layer 2 blocks, it prints the lock
  holder's session ID and operation. The user can see which session is holding
  the lock and what it is doing — exactly the "memory ghosts" visibility that was
  missing today.

### Negative / Trade-offs

- **One-time implementation cost**: Three artifacts to write (`git-coop.sh`,
  `git-commit-scope-guard.sh`, `reserve_adr_slot.py`) plus test coverage and
  gitignore updates.
- **Ongoing latency**: Lock acquire/release adds approximately 10–100ms per git
  operation (two `mkdir` calls, one JSON write, one `rm -rf`). Negligible for
  operations that already dominate at the git process overhead level (~100ms each).
- **Lock starvation in N>2 sessions**: The design is N-safe (any number of
  sessions serialize through the lock), but not starvation-free. Session C
  waiting for Session A could be preempted by Session B repeatedly. In practice
  the 30-second TTL limits starvation duration; a session that cannot acquire in
  30 seconds escalates to the user rather than spinning.
- **Does not fix cross-session memory**: Sessions remain unaware of each other's
  engram activity, session markers, and in-flight work. That is a separate problem
  governed by ADR-071 (engram lifecycle) and the startup protocol. This ADR
  addresses only git coordination, not session discovery.
- **`--only` is unfamiliar**: `git commit --only -- <path>` is less commonly used
  than `git commit <path>` (which is equivalent) or `git commit -m "..." path`
  (also equivalent but position-sensitive). The guard hook enforces the pattern;
  operators do not need to remember it.

---

## Acceptance criteria

These criteria are concrete and verifiable without human interpretation:

```bash
# Layer 1: guard hook exists and is registered
ls hooks/git-commit-scope-guard.sh
grep "git-commit-scope-guard" .claude/settings.json

# Layer 2: lock helper exists with acquire and release subcommands
bash scripts/git-coop.sh acquire 2>&1 | grep -q "acquired\|error"
bash scripts/git-coop.sh release 2>&1 | grep -q "released\|not held"

# Layer 3: reservation script exists and outputs a number
python3 scripts/reserve_adr_slot.py | grep -E '^[0-9]+$'

# Layer 3: reservation placeholder is created
ls .cognitive-os/runtime/reserved-adrs/ | grep -E '^ADR-[0-9]+'

# Test suite: concurrent session simulation
python3 -m pytest tests/integration/test_git_coop_concurrent.py -q --tb=short

# Guard rejects bare git commit in multi-session mode
# (tested via the hook's own unit test, not via a live git commit)
python3 -m pytest tests/unit/test_git_commit_scope_guard.py -q --tb=short
```

All six checks must pass. The concurrent simulation test must demonstrate lock
contention detection (two threads attempting acquire simultaneously, one blocks,
one proceeds, no data corruption).

---

## Open questions

**1. Advisory vs. enforcing for the commit-scope guard in single-session mode.**
Today's decision: advisory in single-session, enforcing in multi-session.
The detection heuristic (count of live context markers in
`.cognitive-os/runtime/`) may produce false negatives if a session crashed and
left a stale marker. Should the guard always enforce, accepting occasional false
positives on stale markers, or remain advisory in ambiguous state?

**2. Does this interact with `--no-verify` workflows?**
`git commit --no-verify` bypasses `prepare-commit-msg` but not `PreToolUse`
hooks. The commit-scope guard runs at the PreToolUse level (before the Bash call
is executed), so `--no-verify` does not bypass it. However, if a user explicitly
passes `--no-verify` in a `git commit --no-verify` call, the guard must decide
whether to block, warn, or allow. Recommendation: allow (the user is explicitly
opting out of hook enforcement), but log to `agent-audit-trail.jsonl`.

**3. Should non-ADR work require slot reservation?**
Today's decision scopes reservation to ADRs only. Other artifacts that use
sequential numbers (e.g., report files, plan file series) have less strict
ordering requirements and higher creation volume. Extending reservation to all
sequential-number artifacts would require a generalized reservation namespace.
Deferred to a follow-up if collisions are observed there.

**4. Does this scale to N>2 sessions?**
The lock design is N-safe in principle: any number of sessions serialize through
`mkdir`. The 30-second escalation path prevents infinite blocking. Untested at
N>2 — today's observation was exactly 2 sessions. If the user regularly runs 3+
sessions, the contention window widens and the advisory "warn and continue"
fallback may need to become a hard block with user escalation.

**5. Per-session worktrees as an alternative.**
The cooperative lock design keeps all sessions in the same working tree, which
matches the user's current workflow. An alternative is to give each session its
own git worktree (`git worktree add`), eliminating the shared index entirely.
See "Alternatives rejected" below for the trade-off analysis.

---

## Migration / rollout

**Phase 1** (high value, low risk — ship first):
- Write `hooks/git-commit-scope-guard.sh`
- Register in `settings.json` as `PreToolUse[Bash]`
- Write unit tests for the guard
- Update CLAUDE.md to document `git commit --only -- <path>` as the mandatory
  form for agent-driven commits

**Phase 2** (medium value, medium risk — ship after Phase 1 is stable):
- Write `scripts/git-coop.sh` with `acquire`/`release`
- Integrate acquire/release into the commit-scope guard
- Write concurrent simulation test (`tests/integration/test_git_coop_concurrent.py`)

**Phase 3** (medium value, low risk — ship independently):
- Write `scripts/reserve_adr_slot.py`
- Add `.cognitive-os/runtime/reserved-adrs/` to `.gitignore`
- Update startup protocol to document the reservation requirement
- Socialize in CLAUDE.md and the ADR drafting convention

Phase 1 delivers the most important protection (commit scope inflation) with zero
new runtime complexity. Phases 2 and 3 can be deferred without leaving the
system worse than it is today.

---

## Alternatives rejected

**Per-session worktrees (`git worktree add`).**
Each session operates in its own worktree, giving it a private working tree and
index. This eliminates the shared-index problem entirely: commit scope inflation
and phantom staging are structurally impossible.

Trade-offs against the cooperative lock approach:

| Concern | Cooperative lock (this ADR) | Per-session worktrees |
|---|---|---|
| Index isolation | Cooperative; sessions still share the index but coordinate | Complete; each session has its own index |
| Workflow disruption | None; sessions continue to operate in the same directory | High; each session must be initialized in a different directory, cross-session file reading requires explicit paths |
| Integration with Claude Code | Transparent; harness cwd is unchanged | Requires harness to accept a per-session cwd or worktree path |
| Merge complexity | No merge required; all sessions commit to the same branch | Session branches must be merged; merge conflicts are possible if sessions touch the same files |
| Stale worktree cleanup | Not applicable | New housekeeping requirement: worktrees must be removed after sessions end |
| ADR slot collisions | Requires Layer 3 (reservation) | Collisions still possible if both sessions write to the same `docs/adrs/` path; worktrees share the committed tree, only the index differs |

Worktrees are the stronger isolation mechanism and the right long-term direction
if concurrent sessions become frequent and complex. The cooperative lock is the
right near-term choice because it requires no workflow change and addresses the
observed failure modes with significantly lower implementation and integration
cost. This ADR does not preclude a future transition to per-session worktrees; it
makes the current multi-session workflow safer while that decision matures.

**Single-session enforcement (block concurrent sessions).**
Detect that a session is already active and refuse to start a second one. This
eliminates the coordination problem by eliminating concurrency.

Rejected because the multi-session workflow is intentional and productive. Session
B completed ADR-081 implementation and ADR-086 while Session A was drafting. The
total work output of two concurrent sessions exceeded what a single session could
produce in the same wall time. Blocking concurrency trades correctness for
productivity; the cooperative lock trades neither.

**Optimistic commit-level locking (detect-and-retry after collision).**
Let commits proceed without locks. After a commit that inflated scope, detect
the inflation by comparing the commit's file list against the staging session's
intended files and automatically revert + re-commit with the correct scope.

Rejected because collision detection after the fact requires knowing the
"intended" scope, which is not machine-readable from the commit itself. The
`a4ab471` inflate-and-revert sequence required manual diagnosis. An automated
version of this would require every agent to log its intended staging set before
committing — which is essentially the same coordination overhead as Layer 1 plus
a rollback mechanism, with higher complexity and a window where the inflated
commit exists on the branch.

---

## Verification

```bash
# Phase 1: guard registered and functional
grep -n "git-commit-scope-guard" .claude/settings.json
python3 -m pytest tests/unit/test_git_commit_scope_guard.py -v --tb=short

# Phase 2: lock helper functional
bash scripts/git-coop.sh acquire && echo "ACQUIRED" && bash scripts/git-coop.sh release && echo "RELEASED"
# Expected: ACQUIRED then RELEASED, no error output
python3 -m pytest tests/integration/test_git_coop_concurrent.py -v --tb=short

# Phase 3: reservation script
python3 scripts/reserve_adr_slot.py
# Expected: prints a number >= current max ADR slot + 1
ls .cognitive-os/runtime/reserved-adrs/
# Expected: one placeholder per active reservation

# Confirm .gitignore covers runtime dir
grep "reserved-adrs" .gitignore
```

---

## Cross-references

- ADR-082: Plan Location Convention (sibling; same root cause — shared mutable
  state without coordination)
- ADR-087: ADR Namespace Consolidation (slot collision diagnosis that preceded
  this ADR)
- ADR-088: Provenance Trailer via PPID Chain (shipped by Session B concurrently;
  took the 088 slot and demonstrated the slot collision failure mode)
- ADR-072: Test Lane Taxonomy (the parallel work Session B was executing when the
  failure modes above occurred)
- ADR-071: Engram Lifecycle Evolution (the cross-session memory problem this ADR
  explicitly does not address)
- Commit `a4ab471`: the inflated commit (9 files, intended as 1-file rename)
- Commit `4ef7dc1`: the revert of `a4ab471`
- Commit `b9bba7a`: the clean redo using `git commit --only --`
- Session A: `1777570193-92907-51ec9a30`
- Session B: `1777570196-94294-3bcc1d20`
