---
adr: 326
title: Tombstone — agent-escalation-capabilities plan (Phase 3 tombstoned, Phases 1+2 archived)
status: tombstone
date: 2026-05-18
implementation_status: not-applicable
supersedes: []
superseded_by: ADR-228
implementation_files: []
tier: maintainer
tags: [tombstone, agent-escalation, escalation, model-routing]
---

<!-- ADR_RELATION_CHAIN_EXEMPT: tombstone pointer to ADR-228/ADR-251; not a new implementation scope chain. -->

# ADR-326 — Tombstone (agent-escalation-capabilities Phase 3 superseded by ADR-228)

## Status
Tombstone

<!-- SCOPE: OS -->

**Status**: Tombstone
**Date**: 2026-05-18

---

## Reason

The plan `.cognitive-os/plans/features/agent-escalation-capabilities.md` was
reconciled in two passes (Sonnet 2026-05-10 + Opus refinement 2026-05-11):

- **Phases 1+2** (typed capability signals NEEDS_DEEPER_REASONING / TOOL_ACCESS /
  MORE_CONTEXT / DOMAIN_EXPERT with structured ESCALATION handoff) were marked
  ARCHIVE — parked for reactivation if recurring capability-ceiling incidents
  accumulate (≥3 per quarter) or operator explicitly prioritizes.
- **Phase 3** (budget gate + retry-count tracking + escalation cost reporting)
  was TOMBSTONED in-place because ADR-228 owns retry counts and escalation
  policies per FailureClass, `hooks/dispatch-gate.sh` owns budget gating, and
  `lib/cost_dashboard.py` covers session cost reporting. Reviving Phase 3
  as-written would duplicate that territory without governance value.

No formal ADR-tombstone slot existed for Phase 3. This ADR closes that gap,
following the convention established by ADR-003 / ADR-004 / ADR-005 / ADR-043
/ ADR-046 / ADR-085 / ADR-214 / ADR-229 / ADR-253.

## Original plan

`.cognitive-os/plans/features/agent-escalation-capabilities.md`

Proposed: typed horizontal escalation signals (capability-ceiling detection),
cross-model re-dispatch with context handoff, budget gates, retry-count tracking.

## Why tombstoned

**Phase 3 (budget/retry/cost scope)**: Superseded by coexistence with shipped
substrate — ADR-228 (retry taxonomy + escalation_after_n per FailureClass),
`hooks/dispatch-gate.sh` + dispatch-budget hardening (v0.28.0), and
`lib/cost_dashboard.py`.

**Phases 1+2**: Not tombstoned — archived pending demand signal. The typed
capability-signal protocol (NEEDS_DEEPER_REASONING etc.) is NOT covered by
ADR-228 or ADR-251 and carries non-duplicate value. Reactivate via ADR-254
manifest/audit path when demand signal fires.

## Supersession

- **ADR-228** — retry taxonomy and FailureClass escalation policy (supersedes Phase 3)
- **ADR-251** — agent orchestration adapter boundary (related; does not supersede Phases 1+2)

## Date tombstoned

2026-05-18 (Wave 7 zombie cleanup)

## Slot policy

- ADR-326 is reserved as a tombstone. Do not reuse the number.
- Phase 3 (budget/retry escalation) is not revived. Extend ADR-228 in place for
  future escalation-budget changes.
- Phases 1+2 may be reactivated via a new ADR referencing this one and
  `.cognitive-os/plans/features/agent-escalation-capabilities.md` §Phases 1+2.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
