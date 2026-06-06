---
adr: 335
title: Generic Task Closure Ledger Gate
status: accepted
implementation_status: implemented
date: '2026-06-06'
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos-task-closure-gate
  - scripts/cos_task_closure_gate.py
  - templates/task-closure-ledger.example.json
  - tests/unit/test_cos_task_closure_gate.py
  - tests/red_team/portability/test_cos_task_closure_gate.py
  - tests/red_team/portability/test_cos-task-closure-gate.py
tier: consumer
tags: [closure, evidence, task-ledger, verification, consumer-projects]
classification_basis: portable CLI, schema contract, project-local ledger validation, strict close mode, executable closure gates, and portability tests
---

# ADR-335: Generic Task Closure Ledger Gate

## Status

Accepted — implemented on 2026-06-06.

## Context

Consumer projects sometimes need to track large work fronts where “done” is not a single test lane. A project-specific closure ledger pattern proved useful: each front records whether completion can be claimed, which gate proves closure, which evidence already exists, what remains, and the next primitive/slice.

Cognitive OS already has adjacent anti-false-completion controls:

- high-stakes claim verification at commit/push boundaries;
- EAS validation for requirement-to-acceptance evidence;
- DoD checks for worktree completion;
- closure discipline audits for stale validation infrastructure.

None of those provide a reusable project-local ledger schema for multi-front closure status. Leaving that pattern in each consumer project would force every project to rewrite the same honesty gate.

## Decision

Add a generic task closure ledger primitive:

1. `scripts/cos-task-closure-gate` is the portable shell entrypoint.
2. `scripts/cos_task_closure_gate.py` is the dependency-free implementation.
3. Ledgers use `contract: cos.task-closure-ledger.v1` with `schemaVersion: 1`.
4. The canonical top-level collection is `fronts[]`; `items[]` is accepted as a compatibility alias with a warning.
5. Each front requires:
   - `id`
   - `title`
   - `status`
   - `canClaimComplete`
   - `closureGate`
   - `doneEvidence`
   - `remaining`
   - `nextPrimitive`
6. The invariant is strict: `canClaimComplete=true` requires `status=closed`; `status=closed` requires `canClaimComplete=true`.
7. Open fronts must list `remaining` and `nextPrimitive` so agents cannot claim completion while hiding residual work.
8. `--require-closed` blocks if any front remains open.
9. `--require-gates-passed` requires closed fronts to record gate evidence.
10. `--run-closure-gates` can execute `closureGate` commands for closed/claimable fronts; `--run-all-gates` is explicit for all fronts.

## Consequences

- Consumer projects can keep domain-specific closure ledgers without copying validator logic.
- Agents get a deterministic closeout summary that says what remains and what the next primitive is.
- Project ledgers stay project-owned; the SO owns only the schema and validator.
- Existing EAS/DoD/claim gates remain complementary rather than replaced.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. A valid open-front ledger exits 0 and prints an honest non-claimable summary.
2. `--require-closed` exits non-zero while any front is open.
3. `status=closed` and `canClaimComplete` cannot diverge.
4. Closed fronts can require gate evidence with `--require-gates-passed`.
5. `--run-closure-gates` executes project-local gate commands for closed/claimable fronts and reports failures.
6. The wrapper works from an arbitrary consumer project root.
7. SCOPE: both portability audit covers the Python implementation and shell wrapper.
```

## Verification

```bash
uv run python -m pytest tests/unit/test_cos_task_closure_gate.py tests/red_team/portability/test_cos_task_closure_gate.py tests/red_team/portability/test_cos-task-closure-gate.py -q
scripts/cos-scope-both-portability-audit --strict
```
