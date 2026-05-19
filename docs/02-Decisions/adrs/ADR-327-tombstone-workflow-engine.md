---
adr: 327
title: Tombstone — workflow-engine plan superseded by shipped ADW substrate
status: tombstone
date: 2026-05-18
implementation_status: not-applicable
supersedes: []
superseded_by: ADR-036
implementation_files: []
tier: maintainer
tags: [tombstone, workflow-engine, dag, pipeline]
---

<!-- ADR_RELATION_CHAIN_EXEMPT: tombstone pointer to ADR-036/ADR-226; not a new implementation scope chain. -->

# ADR-327 — Tombstone (workflow-engine plan superseded by shipped ADW substrate)

## Status
Tombstone

<!-- SCOPE: OS -->

**Status**: Tombstone
**Date**: 2026-05-18

---

## Context

The plan `.cognitive-os/plans/features/workflow-engine.md` was reconciled in two
passes (Sonnet 2026-05-10 + Opus refinement 2026-05-11), both agreeing on
TOMBSTONE. The Opus pass strengthened the rationale from doctrine-only to
**tombstone-by-coexistence-with-shipped-substrate**:

- `.cognitive-os/workflows/` already contains `feature-pipeline.yaml` and
  `bugfix-pipeline.yaml`, and `docs/08-References/root/adw-patterns.md`
  documents the ADW model with 5 named pipelines (feature, bugfix, refactor,
  sre, review) — a lightweight declarative workflow capability is already live.
- ADR-036 (sprint orchestration primitives) covers batch launching and canonical
  events. ADR-226 covers the remaining coordination slices.
- Implementing `lib/workflow_engine.py` + `lib/workflow_types.py` +
  WorkflowEngine / WorkflowParser / DAGBuilder / StateManager as proposed would
  directly duplicate the shipped ADW substrate without governance value.
- The cognitive-os doctrine's "Distributed workflow engines: DEFER" clause
  reinforces the result (though this plan targeted a *local* engine, not a
  distributed one — the coexistence argument is primary).

No formal ADR-tombstone slot existed. This ADR closes that gap, following the
convention established by ADR-003 / ADR-004 / ADR-005 / ADR-043 / ADR-046 /
ADR-085 / ADR-214 / ADR-229 / ADR-253.

## Original plan

`.cognitive-os/plans/features/workflow-engine.md`

Proposed: `lib/workflow_engine.py` implementing a YAML-defined DAG executor with
`WorkflowEngine`, `WorkflowParser`, `DAGBuilder`, `StateManager` classes for
SDD pipeline resumability and dependency-aware multi-step workflows.

## Decision

Tombstone the workflow-engine plan and reserve ADR-327 as the auditable closure record. The canonical path is to extend the shipped ADW substrate rather than create a parallel local workflow engine.

## Why tombstoned

**Tombstone-by-coexistence**: The shipped ADW substrate (`.cognitive-os/workflows/`,
`docs/08-References/root/adw-patterns.md`, ADR-036 sprint primitives, ADR-226)
already provides lightweight declarative workflow capability. The proposed
`lib/workflow_engine.py` would duplicate it without adding governance value.

The three unique proposed capabilities (DAG-with-dependencies, pipeline
resumability, SDD-pipeline-as-data) are either already partially covered or
do not have a validated demand signal (≥3 pipeline-failure-recovery incidents).

## Supersession

- **ADR-036** — sprint orchestration primitives; canonical workflow substrate
- **ADR-226** — covers remaining coordination slices
- **`.cognitive-os/workflows/`** — canonical lightweight workflow YAML definitions
- **`docs/08-References/root/adw-patterns.md`** — ADW model reference

## Date tombstoned

2026-05-18 (Wave 7 zombie cleanup)

## Consequences

- ADR-327 remains a tombstone pointer, not a new implementation scope.
- `lib/workflow_engine.py` and `lib/workflow_types.py` are intentionally not created.
- Future resumability or DAG needs must extend ADR-036/ADR-226 or open a new ADR with ADW as the baseline.

## Alternatives rejected

- Implement the proposed workflow engine as-is — rejected because it duplicates the shipped ADW substrate without adding governance value.
- Leave only the stale plan tombstone — rejected because ADR slots provide the repository-wide audit trail for closed architectural work.
- Treat doctrine alone as the reason — rejected because the stronger reason is coexistence with already-shipped workflow primitives.

## Slot policy

- ADR-327 is reserved as a tombstone. Do not reuse the number.
- `lib/workflow_engine.py` and `lib/workflow_types.py` are not created.
- Future DAG/resumability needs: extend ADR-036 in place or open a new ADR
  referencing the ADW substrate as baseline.
- If a Shape-B trigger fires for federation/cluster runtime (per ADR-132),
  revisit via ADR-254 manifest/audit/research-check path — not by reviving
  this plan as-is.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
