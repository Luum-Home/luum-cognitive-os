---
adr: 4
title: Reserved architecture decision slot
status: tombstone
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - scripts/adr_tombstone.py
  - tests/unit/test_adr_tombstone.py
tier: maintainer
tags: [adr, tombstone, governance]
---
# ADR-004: Reserved architecture decision slot

## Status

**Tombstone** — 2026-05-05

## Context

This ADR number is intentionally reserved so the ADR sequence remains contiguous.

This ADR number remains reserved so the project decision ledger stays auditable.
The removed decision content is not active architecture and must not be recreated
under the same number.

ADR-004 is not the canonical project-license decision. Current publication
licensing is represented by the root `LICENSE`, package metadata, release
packaging metadata, and the private pre-launch license-switch log.

## Decision

Keep ADR-004 as a neutral tombstone. Do not reuse this number for a different
decision. If a future decision is needed, allocate a new ADR number through the
canonical ADR authoring flow.

## Consequences

### Positive

- ADR numbering remains contiguous and machine-checkable.
- Historical references to this number resolve to an explicit neutral record.
- Removed decision content stays out of active runtime, docs, hooks, manifests,
  and tests.

### Negative

- The tombstone intentionally preserves only the number, not the removed prose.
- Readers must use surrounding ADR history or git history for deeper archaeology.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Delete the ADR number entirely | Rejected because it creates a silent numbering gap and makes audits ambiguous. |
| Reuse the number for a new decision | Rejected because ADR numbers are stable identifiers, not recyclable slots. |
| Keep removed prose in active docs | Rejected because removed integration details can be mistaken for supported architecture. |

## Verification

```bash
python3 -m pytest tests/unit/test_adr_tombstone.py tests/contracts/test_adr_numbering_integrity.py -q
```
