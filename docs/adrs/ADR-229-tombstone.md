# ADR-229 — Tombstone (consolidated into ADR-228)

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
