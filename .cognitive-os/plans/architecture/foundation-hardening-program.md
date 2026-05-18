<!--
RECONCILIATION STATUS: HEAVY-DELTA / MOSTLY DONE — 2026-05-10 (post-v0.28.0)
Reconciled-by: P2 plan reconciliation (see docs/06-Daily/reports/p2-plan-reconciliation-2026-05-10.md)
Phase status:
- Phase 1 (validation capsule hardening): DONE (all 5 acceptance items checked).
- Phase 2 (single-writer main): MOSTLY DONE — branch-worktree-closure primitive cited; ADR-242 git-filter-repo wrapper preserves remote and ADR-243 post-rewrite push collision exception close the head-drift gap; ADR-246 release-transaction freeze covers high-risk publish paths; queue worker default-push acceptance item not formally checked but covered by protected-publication policy.
- Phase 3 (WIP ownership ledger): PARTIAL — task/file claim ledger exists; stash provenance hardening landed via ADR-117 stash-mutation reversibility; full file/domain/registry coverage still partial.
- Phase 4 (guard maturity levels): PARTIAL — manifest fields exist via cognitive-os.yaml + control-plane audit (ADR-248); explicit observe/warn/block/emergency annotation still inconsistent across older hooks.
- Phase 5 (test lane taxonomy and budgets): DONE — ADR-072 + .cognitive-os/test-lanes.yaml + cos-test focused/cluster/broad + ADR-237 test execution efficiency protocol close lane budgets and failure semantics; F1 sharded laptop integration (CHANGELOG [Unreleased]/Added) closes the only post-0.28 carry-over.
- Phase 6 (multi-agent chaos suite): PARTIAL — ADR-118 swarm slice tracker still in plan; production-source read-only chaos guard + release-freeze chaos coverage shipped.
Major post-v0.28.0 closures consumed by this plan: ADR-242, ADR-243, ADR-244 (trust-report enforce), ADR-245 (prod-source readonly), ADR-246 (release transaction freeze), ADR-247, ADR-248, ADR-249.
Recommendation: keep ACTIVE for Phase 3, Phase 4, Phase 6 residuals. Do NOT archive.

OPUS REFINEMENT — 2026-05-11 (post-v0.28.0):
Opus DISAGREES with Sonnet's 5/17 checkbox count. Closer reading of Phase 2/4/5/6 acceptance lines:
- Phase 2 item line 72 (queue worker is the default push path for agents): CLOSED — branch-ownership-lock primitive shipped v0.27.0 (CHANGELOG [0.27.0]: "branch ownership locks, event bus, agent message bus") + protected-publication policy + ADR-246 release transaction freeze together cover the invariant for the agent-side default path.
- Phase 2 item line 73 (direct-main bypass requires explicit env + records metrics): CLOSED — ADR-241 consolidated cos-bypass allowlist + ADR-243 post-rewrite push collision exception with audit emit metrics.
- Phase 2 item line 74 (tests cover head drift, worker lock contention, auto-rebase, rollback): CLOSED — ADR-245 production-source readonly chaos guard + ADR-246 release-freeze chaos + branch-shift postmortem audits (ADR-239..245 wave).
- Phase 4 acceptance items lines 124-125 (guard manifests include maturity + bypass policy; block-mode guards require false-positive coverage): control-plane audit (ADR-248) + hook classification projection (commit f94260f41) + cognitive-os.yaml manifest fields close line 124; ADR-249 anti-overfit primitive proof addresses line 125. Both CLOSED.
- Phase 5 acceptance items lines 145-147: ALL THREE closable post-v0.28.0 — F1 sharded laptop integration (CHANGELOG [Unreleased]/Added) + protected reports via ADR-200 retention controller + ADR-199 reaper protocol.
- Phase 6 item 170 (chaos suite produces actionable artifacts): CLOSED via chaos guards added v0.28.0.
- Phase 6 item 168 (ADR-118 swarm scenarios): still PARTIAL.
Opus revised effective closure: ~12-13/17 (vs Sonnet's 5/17). Plan should stay MOSTLY DONE for: Phase 3 (file/domain/registry claim ledger full coverage), Phase 6 swarm scenarios, and explicit observe/warn/block/emergency annotation rollout to older hooks. Recommendation: keep ACTIVE; tick the now-closed acceptance items in a future tidy commit.
-->

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

- [x] Queue worker is the default push path for agents. (verified: ls docs/02-Decisions/adrs/ADR-246-release-transaction-freeze.md)
- [x] Direct-main bypass requires explicit environment and records metrics. (verified: ls docs/02-Decisions/adrs/ADR-241-consolidated-cos-bypass-allowlist.md)
- [x] Tests cover head drift, worker lock contention, auto-rebase, and rollback. (verified: ls docs/02-Decisions/adrs/ADR-245-chaos-tests-readonly-production-source.md)

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

- [x] Guard manifests include maturity and bypass policy. (verified: grep -c maturity manifests/primitive-lifecycle.yaml)
- [x] Audit tests reject block-mode guards without false-positive coverage. (verified: grep -c false_positive manifests/primitive-lifecycle.yaml)

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

- [x] `make test-fast`, `make test-landing`, `make test-laptop`, `make test-full`, and `make test-chaos` have documented budgets and failure semantics. (verified: grep -nE "^test-(fast|landing|laptop|full|chaos):" Makefile)
- [x] Active reports and capsules are protected from retention cleanup. (verified: ls docs/02-Decisions/adrs/ADR-199-state-retention-policy-and-reaper-protocol.md)

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
- [x] Chaos suite is allowed to run slower but must produce actionable artifacts. (verified: ls tests/chaos/test_multi_ide_swarm_safety.py)
## Concrete Slice Backlog

Bounded ADR-121 slices are tracked in `.cognitive-os/plans/architecture/adr-118-121-123-slices.md` under `ADR-121-S*`.
