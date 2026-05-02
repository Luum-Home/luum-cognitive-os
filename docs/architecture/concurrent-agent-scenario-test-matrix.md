# Concurrent Agent Scenario Test Matrix

> Status: draft
> Updated: 2026-05-02
> Scope: automated scenarios that reproduce realistic concurrent-agent failures
> Related: [ADR-108](../adrs/ADR-108-concurrent-agent-safety-layer.md), [Concurrent Agent Safety Master](concurrent-agent-safety-master.md), [Concurrent Agent Safety Testbed Plan](../../.cognitive-os/plans/architecture/concurrent-agent-safety-testbed-plan.md)

## Rule

Every scenario in this matrix must be automated. Manual reproduction may help during development, but it does not satisfy acceptance criteria.

## Mandatory First Slice

| Priority | Scenario | Realistic failure | Expected behavior | Proposed automated test | Lane |
|---|---|---|---|---|---|
| 1 | Two agents edit the same file | Last writer silently overwrites first writer | Second writer is blocked, parked, or receives structured conflict; first edit survives | `tests/integration/test_concurrent_agent_same_file.py` | integration |
| 2 | False done in plan | `[x]` becomes shared false truth after optimistic-only verification | Plan closure without bilateral proof is rejected or flagged; valid proof passes | `tests/behavior/test_plan_false_done_gate.py` | behavior |
| 3 | Stash leak | Auto-pre-agent stash hides work from later sessions | Alarm JSON is written; strict/block TTL prevents unsafe dispatch | `tests/behavior/test_stash_leak_alarm.py` | behavior |

## Scenario 1 — Two Agents Edit The Same File

### Accident To Reproduce

Session A and Session B both believe they can edit `target.txt`. Without a file lock, whichever write lands last wins and the earlier work is silently lost.

### Automated Fixture

- Create a temporary git repository.
- Create `target.txt`.
- Use environment variables to simulate `COGNITIVE_OS_SESSION_ID=A` and `COGNITIVE_OS_SESSION_ID=B`.
- Session A acquires an edit lock for `target.txt`.
- Session B attempts to acquire or write `target.txt`.

### Expected Assertions

- Session B receives non-zero conflict result.
- Conflict output includes holder metadata.
- `target.txt` still contains Session A's content.
- After Session A releases, Session B can acquire.

### Command

```bash
python3 -m pytest tests/integration/test_concurrent_agent_same_file.py -v
```

## Scenario 2 — False Done In Plan

### Accident To Reproduce

A plan item is marked `[x]` based on optimistic partial verification. Example: an archive copy exists, but the original file still exists or config still references it.

### Automated Fixture

- Create a scratch plan file.
- Create a claim such as `Archive hook example.sh`.
- Create only the optimistic half of the evidence.
- Attempt to close the checkbox without `(verified: ...)` proof.
- Run the checker.
- Add full bilateral proof and rerun.

### Expected Assertions

- Bare `[x]` on a high-stakes claim fails.
- Optimistic-only proof fails.
- Complete bilateral proof passes.
- Error text names the missing inverse condition.

### Command

```bash
python3 -m pytest tests/behavior/test_plan_false_done_gate.py -v
```

## Scenario 3 — Stash Leak

### Accident To Reproduce

`pre-agent-snapshot.sh` or equivalent creates an `auto-pre-agent-*` stash. The stash disappears from `git status`, leaving later agents unaware of hidden work.

### Automated Fixture

- Create a scratch git repository.
- Commit initial file.
- Modify file and create an `auto-pre-agent-test-*` stash.
- Run detector with `COS_STASH_LEAK_TTL=0`.
- Run detector with `COS_STASH_LEAK_BLOCK_TTL=0`.

### Expected Assertions

- Alarm JSON appears under `.cognitive-os/runtime/stash-leak-alarm.json`.
- Alarm includes stash ref, message, age, file count, and blocking flag.
- Strict/block mode exits non-zero with actionable remediation text.
- Test does not mutate the developer's real repository or real stash.

### Command

```bash
python3 -m pytest tests/behavior/test_stash_leak_alarm.py -v
```

## Backlog Scenarios

| Scenario | Realistic failure | Expected behavior | Proposed test |
|---|---|---|---|
| Concurrent commits | Two sessions commit to same branch with no attribution | Missing provenance fails or doctor reports untraceable commit | `tests/integration/test_concurrent_commit_provenance.py` |
| Same primitive, different files | Agents edit different files but same logical primitive | Resource lease conflict or warning appears | `tests/behavior/test_resource_lease_conflict.py` |
| Out-of-scope edit | Agent edits beyond declared scope | Post-agent verifier rejects or parks change | `tests/behavior/test_out_of_scope_agent_edit.py` |
| Approval bypass | Agent uses bypass flag | Override ledger records actor, scope, reason, timestamp | `tests/behavior/test_override_ledger.py` |
| Cross-worktree divergence | Worktrees close conflicting plan state | Reconciler reports divergence before merge | `tests/integration/test_cross_worktree_plan_reconciler.py` |
| Delete/recreate repair | Small fix becomes destructive rewrite | Destructive/high-blast gate blocks or requires approval | `tests/behavior/test_delete_recreate_repair_gate.py` |

## Automation Requirements

- Use temporary directories or scratch repos.
- Simulate agents with subprocesses and environment variables.
- Do not require real concurrent humans.
- Do not use real wall-clock waiting; TTLs must be environment-controlled.
- Do not mutate the developer's actual stash or production worktree.
- Tests must be deterministic on macOS and Linux.
