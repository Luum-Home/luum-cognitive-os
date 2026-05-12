---
adr: 229
title: Tombstone (consolidated into ADR-228)
status: tombstone
implementation_status: not-applicable
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit prose status migration for previously prose-only ADR
---

# ADR-229 — Tombstone (consolidated into ADR-228)

status: tombstone

## Status
Tombstone


<!-- SCOPE: OS -->

**Status**: Tombstone
**Date**: 2026-05-06

---

## Reason

ADR-229 was originally proposed in [`SYNTHESIS-2026-05-06.md`](../research/orchestration-gaps/SYNTHESIS-2026-05-06.md) as the standalone "Session Budget Pre-Call Gate" ADR for gap G8 (cost-aware routing).

During Phase-1 ADR drafting, the synthesis flagged ADR-228 (retry contract) and ADR-229 (cost budget) as a consolidation candidate because both:

- live in the same code path (`lib/dispatch.py` → `lib/dispatch_gate.py`)
- need a synchronous pre-call gate
- share file-backed state under `.cognitive-os/metrics/`
- consume the ADR-226 event sequence for session attribution

Splitting into two ADRs would have forced two parallel modifications to `dispatch()` and two adjacent test suites without added clarity. The decision was to consolidate.

## Canonical authority

See **[ADR-228 — Retry Contract + Cost Session Budget (consolidated)](ADR-228-retry-contract-and-cost-budget.md)**.

## Slot policy

- ADR-229 is reserved as a tombstone. Do not reuse the number for unrelated work.
- Future work on cost-aware routing extends ADR-228 in place or supersedes it; it does not re-occupy ADR-229.
- This mirrors the precedent set by ADR-214 (also a tombstone, vacated for a parallel-session collision).

## Context
This ADR was backfilled into the ADR-067 section contract after the decision had already been recorded. The original context remains in the existing sections above; this section exists so the ADR can be audited uniformly.

## Decision
Keep the decision described in this ADR as the canonical project policy for this slot. Implementation-specific details remain in the sections above and in the files referenced by this ADR.

## Consequences
- The ADR can be checked by the common ADR contract audit.
- Future amendments must preserve this decision record instead of relying on conversation history.

## Alternatives rejected
- Reusing this ADR number for a different decision — rejected because tombstones preserve numbering provenance and prevent contradictory references.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
