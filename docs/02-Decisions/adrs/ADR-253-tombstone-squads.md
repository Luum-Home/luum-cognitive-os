---
adr: 253
title: Tombstone — squads orchestration superseded by ADR-251
status: tombstone
date: 2026-05-08
implementation_status: not-applicable
supersedes: []
superseded_by: ADR-251
implementation_files: []
tier: maintainer
tags: [tombstone, squads, orchestration]
---

<!-- ADR_RELATION_CHAIN_EXEMPT: tombstone pointer to ADR-251; not a new implementation scope chain. -->

# ADR-253 — Tombstone (squads orchestration superseded by ADR-251)

## Status
Tombstone

<!-- SCOPE: OS -->

**Status**: Tombstone
**Date**: 2026-05-08

---

## Reason

The `packages/squads/` orchestration package (multi-agent team coordination
via YAML squad definitions) was archived to `packages/_archived/squads/`
during Sprint 2A on 2026-04-16 after the audit recorded in
`docs/04-Concepts/architecture/functional-audit/scorecard-packages-squads-agents.md`
(F5–F8: 0% runtime integration). The de-facto tombstone lives in
`packages/_archived/squads/README.md` but no formal ADR-tombstone existed,
breaking the convention set by ADR-003 / ADR-004 / ADR-005 / ADR-043 /
ADR-046 / ADR-085 / ADR-214 / ADR-229. This ADR closes that gap.

The redesigned orchestration boundary is **ADR-251 (Agent Orchestration
Adapter Boundary)** — Accepted, Slice A implemented. ADR-251 keeps
governance and orchestration as separate axes (the original squads design
collapsed them, which was the root cause of 0% runtime integration).

## Canonical authority

See **[ADR-251 — Agent Orchestration Adapter Boundary](ADR-251-agent-orchestration-adapter-boundary.md)**.

## Slot policy

- ADR-253 is reserved as a tombstone. Do not reuse the number.
- Squads-style team coordination is not revived. Future multi-agent
  coordination work extends ADR-251 in place or supersedes it.
- The archived YAMLs in `packages/_archived/squads/` are reference-only
  and may be deleted in a future cleanup without further ADR.

## Context
Surfaced by `docs/06-Daily/reports/cross-check-C-orchestration-2026-05-08.md` §🔍3
during the 2026-05-08 tech-radar cross-check pass. The audit confirmed:
intentional dormancy, ADR-251 is the redesign, but the formal ADR-tombstone
slot was empty.

## Decision
Record the squads archival as a tombstone so the ADR contract audit
(`tests/audit/test_adr_contracts.py`) passes uniformly across the
ADR-tombstone series and future readers find the supersedence pointer
without spelunking the archived README.

## Consequences
- Convention restored: every archived component has a tombstone ADR with
  `Superseded-by` pointer.
- Cross-reference: `packages/_archived/squads/README.md` ↔ ADR-251 via this
  ADR.
- Future cleanups of `packages/_archived/squads/` do not require a new ADR.

## Alternatives rejected
- Leaving the README as the only tombstone — rejected because it's outside
  the ADR audit scope and breaks the convention precedent.
- Reviving squads under a new name — rejected; ADR-251 is the redesign and
  decouples governance from orchestration.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
