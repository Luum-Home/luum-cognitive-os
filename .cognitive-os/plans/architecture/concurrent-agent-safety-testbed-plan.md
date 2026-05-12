---
related-docs:
  - docs/04-Concepts/architecture/concurrent-agent-safety-master.md
  - docs/04-Concepts/architecture/concurrent-agent-scenario-test-matrix.md
  - docs/02-Decisions/adrs/ADR-108-concurrent-agent-safety-layer.md
  - docs/02-Decisions/adrs/ADR-089-multi-session-git-coordination.md
  - docs/02-Decisions/adrs/ADR-098-multi-agent-file-coordination.md
  - docs/02-Decisions/adrs/ADR-105-claim-verification-contract.md
  - docs/02-Decisions/adrs/ADR-106-multi-session-safety-primitives.md
status: implemented-initial-slice
created: 2026-05-02
---

# Concurrent Agent Safety Testbed Plan

> Goal: implement automated scenario tests that reproduce realistic concurrent-agent failures and prove Cognitive OS primitives prevent or detect them.

## Operating Rule

All proof in this plan is automatic. Manual validation may be used while debugging, but it does not satisfy acceptance criteria.

## Implementation Order

1. Scenario matrix first.
2. ADR second.
3. Implement Scenario 1: two agents edit the same file.
4. Implement Scenario 2: false done in plan.
5. Implement Scenario 3: stash leak.

## Phase 0 — Scenario Matrix

### Deliverable

`docs/04-Concepts/architecture/concurrent-agent-safety-master.md` contains the canonical scenario matrix and acceptance criteria.

### Acceptance Criteria

```bash
test -f docs/04-Concepts/architecture/concurrent-agent-safety-master.md
grep -q "Two agents edit the same file" docs/04-Concepts/architecture/concurrent-agent-safety-master.md
grep -q "False done in plan" docs/04-Concepts/architecture/concurrent-agent-safety-master.md
grep -q "Stash leak" docs/04-Concepts/architecture/concurrent-agent-safety-master.md
```

## Phase 1 — ADR

### Deliverable

Create `docs/02-Decisions/adrs/ADR-108-concurrent-agent-safety-layer.md`.

### Required Decision

The ADR should decide that Cognitive OS owns a Concurrent Agent Safety Layer composed of:

- agent work ledger;
- resource leases;
- file/git/plan locks;
- claim verification registry;
- provenance;
- cross-session reconciler;
- approval/override ledger;
- automated scenario tests.

### Acceptance Criteria

```bash
test -f docs/02-Decisions/adrs/ADR-108-concurrent-agent-safety-layer.md
grep -q "Concurrent Agent Safety Layer" docs/02-Decisions/adrs/ADR-108-concurrent-agent-safety-layer.md
grep -q "automated scenario" docs/02-Decisions/adrs/ADR-108-concurrent-agent-safety-layer.md
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

## Phase 2 — Scenario 1: Two Agents Edit The Same File

### Purpose

Prove that two simulated agents cannot silently overwrite the same file.

### Candidate Implementation

Add:

- `tests/integration/test_concurrent_agent_same_file.py`
- optionally `scripts/concurrency_scenario_fixture.py` if fixture setup grows.

### Test Shape

1. Create an isolated scratch git repo.
2. Create `target.txt`.
3. Simulate Session A acquiring edit lock through `scripts/edit-coop.sh`.
4. Simulate Session B attempting lock acquisition on the same path.
5. Assert Session B exits with conflict code.
6. Assert conflict output includes holder metadata.
7. Assert Session B did not overwrite `target.txt`.
8. Release lock and assert Session B can acquire after release.

### Acceptance Criteria

```bash
python3 -m pytest tests/integration/test_concurrent_agent_same_file.py -v
```

### Failure Must Be Reproduced

The test should include or document the unsafe baseline: without the lock, last writer wins. The protected path must prove that overwrite is blocked.

## Phase 3 — Scenario 2: False Done In Plan

### Purpose

Prove that high-stakes plan closure requires bilateral verification.

### Candidate Implementation

Add:

- `tests/behavior/test_plan_false_done_gate.py`
- helper script if needed: `scripts/verify-plan-claims.py`

### Test Shape

1. Create scratch plan file with an archive/remove/done claim.
2. Create only optimistic partial evidence.
3. Attempt to mark `[x]` without `(verified: ...)`.
4. Run checker.
5. Assert failure.
6. Add complete bilateral proof.
7. Assert pass.

### Acceptance Criteria

```bash
python3 -m pytest tests/behavior/test_plan_false_done_gate.py -v
```

### Failure Must Be Reproduced

The failing fixture must mimic the real error: archive copy exists, but original file or config reference still exists.

## Phase 4 — Scenario 3: Stash Leak

### Purpose

Prove that hidden auto-pre-agent stashes surface automatically and can block unsafe continuation in strict mode.

### Candidate Implementation

Add:

- `tests/behavior/test_stash_leak_alarm.py`
- helper script if needed: `scripts/stash-leak-alarm.sh`

### Test Shape

1. Create isolated scratch git repo.
2. Create tracked file and dirty change.
3. Create stash named `auto-pre-agent-test-*`.
4. Run detector with `COS_STASH_LEAK_TTL=0`.
5. Assert alarm JSON exists.
6. Run detector with `COS_STASH_LEAK_BLOCK_TTL=0`.
7. Assert blocking exit and actionable remediation text.

### Acceptance Criteria

```bash
python3 -m pytest tests/behavior/test_stash_leak_alarm.py -v
```

### Failure Must Be Reproduced

The fixture must prove the stash is invisible to normal `git status` but visible to the detector.

## Phase 5 — Doctor

### Purpose

Once the first three scenarios exist, expose a summarized proof command.

### Candidate Command

```bash
bash scripts/cos-doctor-concurrency.sh
```

Future Go CLI:

```bash
cos doctor concurrency
```

### Acceptance Criteria

```bash
bash scripts/cos-doctor-concurrency.sh --strict
python3 -m pytest tests/behavior/test_cos_doctor_concurrency.py -v
```

## Test Isolation Requirements

- Tests must use temp directories or scratch repos.
- Tests must not mutate the developer's real stash.
- Tests must not depend on real wall-clock waiting; TTLs must be env-controlled.
- Tests must not require parallel humans; subprocesses/environment variables simulate sessions.
- Tests must be deterministic on macOS and Linux.

## Definition of Done

- Master document exists.
- ADR exists.
- Three mandatory scenarios are automated.
- `cos doctor concurrency` or shell fallback summarizes the posture.
- Docs link the testbed from `docs/00-MOCs/entrypoints/README.md` and the master checklist.

## Implementation Evidence

Initial slice implemented on 2026-05-02:

```bash
python3 -m pytest tests/integration/test_concurrent_agent_same_file.py tests/behavior/test_plan_false_done_gate.py tests/behavior/test_stash_leak_alarm.py -v
bash scripts/cos-doctor-concurrency.sh --strict
```

Expected evidence from the implementation session:

- `7 passed` for the three scenario test files.
- `Result: PASS (0 warning(s))` for `scripts/cos-doctor-concurrency.sh --strict`.

Implemented files:

- `scripts/verify-plan-claims.py`
- `scripts/stash-leak-alarm.sh`
- `scripts/cos-doctor-concurrency.sh`
- `tests/integration/test_concurrent_agent_same_file.py`
- `tests/behavior/test_plan_false_done_gate.py`
- `tests/behavior/test_stash_leak_alarm.py`
