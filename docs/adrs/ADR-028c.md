---
adr: 28c
title: 'Addendum: MetricEvent schema versioning + migration strategy'
status: accepted
implementation_status: partial
date: '2026-04-20'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
---

# ADR-028c — Addendum: MetricEvent schema versioning + migration strategy

**Status**: Accepted (closes ADR-028 open question #4)
**Date**: 2026-04-20

## Decision

MetricEvent.schema_version is a monotonically-increasing integer starting at 1.
Changes are classified:

- **Additive (minor)**: add optional field to `payload` or top-level. No version bump.
  Readers MUST tolerate unknown fields (existing `from_dict` already folds extras into payload).
- **Semantic (backward-compatible)**: redefine existing field meaning while preserving shape.
  Version stays the same; document in `docs/adrs/ADR-028c-schema-changelog.md` (create when first used).
- **Breaking (major)**: rename/remove required field, change type, restructure payload.
  Version increments by 1. Migration script MUST ship in same commit under
  `scripts/migrate_metric_event_v{N}_to_v{N+1}.py`.

## Migration contract

A breaking change requires:
1. Increment `lib.metric_event.SCHEMA_VERSION`.
2. Ship `scripts/migrate_metric_event_v{old}_to_v{new}.py` — reads old JSONL,
   writes new-shape JSONL, preserves all fields.
3. Update `lib.metric_event.from_dict` to handle BOTH old and new schema_version
   values (transitional reader).
4. Add pytest tests asserting old JSONL rows still parse + migrate cleanly.
5. After one release cycle (2 weeks min), remove old-schema tolerance.

## Reader tolerance guarantee

`lib.metric_event.from_dict(d)` MUST NOT raise on any schema_version >= 1.
Unknown schema_version → best-effort parse with sensible defaults (source="unknown",
event_type="legacy"). This is tested in `tests/unit/test_metric_event.py`.

## Breaking changes since v1

(None yet — v1 is the only shipped schema.)
