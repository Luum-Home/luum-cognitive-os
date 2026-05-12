---
adr: 237
title: Test Execution Efficiency Protocol
status: accepted
implementation_status: implemented
date: '2026-05-07'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit accepted/implemented status
---

# ADR-237 — Test Execution Efficiency Protocol

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted — Slice A implemented (2026-05-07)  
**Date**: 2026-05-07  
**Related**: ADR-211 (service readiness), ADR-226 (event-sourced bus), ADR-228 (retry/budget), test-tier matrix C3 in `manifests/orchestration-research-evaluation.yaml`

---

## Context

Cognitive OS test lanes are intentionally broad: unit, behavior, integration, chaos, benchmark, audit, smoke, cross-harness, and release gates. Running `make test-laptop` or larger lanes after every small repair wastes laptop time, burns tokens, and encourages low-quality loops: fix one failure, rerun everything, discover the next failure, repeat.

For SO maintenance, the correct workflow is batch-oriented:

1. Run the smallest lane that can reveal the likely failure class.
2. Collect all failures in that lane.
3. Repair the full batch.
4. Rerun the affected lane/group, not the whole suite.
5. Only after targeted groups pass, run the broader laptop lane once.

This is not a consumer-project rule. It is an SO-maintainer primitive for this repository.

## Decision

Add a repository-local test efficiency primitive:

- `manifests/test-execution-efficiency.yaml` — policy and lane ordering.
- `lib/test_efficiency_planner.py` — deterministic planner from changed files/failure text to lane groups.
- `scripts/cos-test-efficiency-plan` — CLI that emits JSON or shell commands.
- `.codex/skills/test-efficiency/SKILL.md` — maintainer workflow skill for this repo.

The primitive does **not** skip tests permanently. It stages test execution so the broad lane runs after targeted repairs, not after every edit.

## Hard rules

- Broad laptop/release lanes are not first response unless the change is already validated or the user explicitly requests immediate broad validation.
- If a broad lane fails, do not immediately rerun it. Extract failing node IDs, repair the batch, and rerun grouped targeted lanes first.
- Integration/chaos/e2e lanes run serially and only when touched paths or prior failures justify them.
- The planner may recommend `make test-laptop` as the final confidence lane, but never as the first lane for a multi-file repair.

## Implementation status

Slice A implemented:

- Manifest-backed policy.
- CLI planner with `--changed-file`, `--failure-file`, `--commands`, and `--include-final-laptop`.
- Skill workflow for SO maintainers.
- Unit, behavior, and audit tests proving lane selection and policy invariants.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_test_efficiency_planner.py \
  tests/behavior/test_cos_test_efficiency_plan_cli.py \
  tests/audit/test_test_execution_efficiency_manifest.py -q
```

The tests must prove:

- Runtime/lib changes select unit + behavior lanes before laptop.
- Chaos failures select chaos rerun lanes without triggering laptop first.
- Docs-only changes select docs/audit guardrails.
- Manifest forbids broad-first execution by default.

## Consequences
- The ADR can be checked by the common ADR contract audit.
- Future amendments must preserve this decision record instead of relying on conversation history.

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
