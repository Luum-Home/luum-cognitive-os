---
adr: 214
title: Reserved — vacated by parallel-session number collision
status: tombstone
date: 2026-05-06
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: [adr, tombstone, governance]
---

# ADR-214: Reserved — vacated by parallel-session number collision

## Status

**Tombstone** — 2026-05-06

## Context

This ADR number was briefly used during a parallel-session collision on
2026-05-06. Two concurrent agent sessions independently picked ADR-214 for
distinct decisions:

- Session A drafted `ADR-214-cross-stack-secret-audit-toolchain.md` (later
  renumbered to **ADR-215**).
- Session B drafted `ADR-214-tool-discovery-pre-use-gate.md` (later renumbered
  to **ADR-216**).

Neither was ever committed under the number 214. The slot was vacated cleanly
before any reference landed in main-branch history.

## Decision

Keep ADR-214 as a neutral tombstone. Do not reuse this number for a different
decision.

The acknowledged sibling decisions live at:

- ADR-215 — Cross-Stack Secret Audit Toolchain
- ADR-216 — Tool Discovery Pre-Use Gate

## Operational lesson

ADR number assignment lacks a coordination primitive across parallel sessions.
ADR-216 (Tool Discovery Pre-Use Gate) and ADR-098 (Multi-Agent File
Coordination) together address the broader category. A future amendment may
add ADR-number reservation to the coordination contract; until then, parallel
sessions accept that number collisions resolve via the first commit to land,
and tombstones document the vacated slots.
