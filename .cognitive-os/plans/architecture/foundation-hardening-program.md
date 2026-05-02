# Foundation Hardening Program

## Goal

Turn the current robust-but-heavy Cognitive OS into a production-stable
multi-agent operating system by replacing human/agent discipline with explicit
transactions, claims, lanes, guard maturity, and chaos verification.

## Phase 1 — Validation capsule hardening

### Invariants

- A validation capsule is an immutable HEAD transaction.
- Active validation capsules are protected by PID + heartbeat; semantic activity
  is diagnostic and cannot override a live PID/heartbeat.
- Cleanup tools and reapers must skip active capsules and report why.
- Stale/corrupt validation state fails closed unless a stale owner is proven.

### Production border cases

- Live PID + fresh heartbeat + old activity log: keep lock and capsule.
- Live PID + missing activity log: keep lock and capsule.
- Dead PID + stale heartbeat + old activity: cleanup allowed after backup.
- Corrupt lock with capsule path: fail closed and skip removal.
- Lock points to another capsule: do not protect unrelated stale capsule.
- Validation lane runs longer than activity threshold: no mid-run deletion.
- Cleanup runs while pytest has cwd/open files in capsule: skip removal.

### Acceptance

- [x] `validation-lock-cleanup.sh` keeps live quiet capsules.
- [x] `cos_validation_lock_active` keeps live quiet locks.
- [x] `cos_cleanup_preserved_wip.py` skips active locked capsules.
- [x] `cos_cleanup_preserved_wip.py` skips capsules with active processes even
      without a lock.
- [x] `cos_cleanup_preserved_wip.py` removes dead/stale validation capsules only
      after backup.

## Phase 2 — Single-writer main

### Invariants

- Direct pushes to `main` are blocked for agents and discouraged for operators.
- Merge queue re-fetches remote main immediately before landing.
- Landing is fast-forward or explicit rebase + revalidation.
- Post-merge verification can auto-revert or park a failed landing.

### Production border cases

- Remote main advances after local validation.
- Two workers try to push simultaneously.
- Rebase conflict in generated artifacts.
- Post-merge verification fails after push.
- Operator emergency bypass is logged and auditable.

### Acceptance

- [ ] Queue worker is the default push path for agents.
- [ ] Direct-main bypass requires explicit environment and records metrics.
- [ ] Tests cover head drift, worker lock contention, auto-rebase, and rollback.

### Agent closure primitive

Agents MUST use the `branch-worktree-closure` skill whenever they find a leftover
`codex/*`, `claude/*`, or other agent-owned branch/worktree. The primitive
turns cleanup into an explicit classify → rebase → validate → merge-queue →
remove workflow, preventing agents from force-deleting useful work or pushing
directly to `main`.

## Phase 3 — WIP ownership ledger

### Invariants

- Task/file/domain/stash/worktree ownership is explicit and TTL-bound.
- Duplicate ownership blocks or parks work instead of allowing silent overlap.
- Claims survive process crashes long enough for reapers to diagnose.

### Production border cases

- Two agents choose same pending task.
- Two agents edit same file set.
- One agent owns registry/projection while another regenerates artifacts.
- Stash belongs to an old session and must not be silently reapplied elsewhere.
- Worktree is dirty, detached, or patch-equivalent to main.

### Acceptance

- [ ] File/domain claim ledger covers registry, projections, ADRs, hooks, tests.
- [ ] Stash provenance blocks ambiguous reapply/cleanup.
- [ ] Work inventory reports owners and conflict actions.

## Phase 4 — Guard maturity levels

### Invariants

- Every guard declares `observe`, `warn`, `block`, or `emergency` maturity.
- New guards ship with false-positive tests before block mode.
- Emergency bypasses are scoped, time-limited, and logged.

### Production border cases

- Guard sees generated files, submodules, symlinks, binary files, and deleted
  files.
- Guard runs in consumer repo without full SO layout.
- Guard sees valid operator action that resembles agent mutation.
- Guard dependency (`jq`, `python3`, `git`) is missing.

### Acceptance

- [ ] Guard manifests include maturity and bypass policy.
- [ ] Audit tests reject block-mode guards without false-positive coverage.

## Phase 5 — Test lane taxonomy and budgets

### Invariants

- Lanes are selected by risk and operational intent, not habit.
- Fast checks are commit-time; landing checks are queue-time; laptop checks are
  high-confidence local; full/chaos are CI/nightly.
- Heavy lanes emit runtime, rerun, and flaky-worker telemetry.

### Production border cases

- xdist worker crash and rerun recovery.
- Timeout in one lane while others passed.
- Test reports pruned while run is active.
- Validation capsule cleanup while behavior lane is running.

### Acceptance

- [ ] `make test-fast`, `make test-landing`, `make test-laptop`, `make test-full`,
      and `make test-chaos` have documented budgets and failure semantics.
- [ ] Active reports and capsules are protected from retention cleanup.

## Phase 6 — Multi-agent chaos suite

### Invariants

- Chaos tests simulate real concurrent agents, not only unit-level mocks.
- Every previously observed race gets a reproducer.
- Chaos failures park work safely instead of corrupting main or losing WIP.

### Production border cases

- Agent modifies registry while another regenerates projections.
- Validation runs while cleanup/reaper starts.
- Merge queue worker races another worker.
- Direct push is attempted during queued landing.
- Stash reapply happens after branch moved.
- Hook safe-mode/kill-mode is triggered during startup latency.

### Acceptance

- [ ] ADR-118 swarm scenarios cover same-task, same-file, same-domain,
      projection drift, stash reapply, validation cleanup, and merge queue races.
- [ ] Chaos suite is allowed to run slower but must produce actionable artifacts.
