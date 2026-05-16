---
adr: 39
title: Reinvention Phase B-beta (semantic embeddings)
status: proposed
implementation_status: planned
date: '2026-04-20'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit prose status migration for previously prose-only ADR
---

# ADR-039 — Reinvention Phase B-beta (semantic embeddings)

> Originally drafted in `.cognitive-os/pending-tasks/adr-039-reinvention-phase-b-beta.md`; canonical location is `docs/02-Decisions/adrs/`.

## Status

Proposed

## Gap
ADR-029b Phase B-alpha (Jaccard over docstrings+function names, shipped 2026-04-20 commit `7008f58`) has LOW precision on real corpus:
- Threshold 0.3, observed scores 0.05-0.15 for genuine matches
- Almost never fires in practice
- ADR documents this was expected — "tuning follow-up work"

## Scope
Upgrade to embedding-based similarity:
- Install `sentence-transformers` (or bge-small-en-v1.5, all-MiniLM-L6-v2 — <50MB local)
- Replace `lib/reinvention_semantic.py::find_similar()` Jaccard with cosine on embeddings
- Precompute index in parallel (threading) on SessionStart
- Re-calibrate threshold from real corpus benchmark

## Acceptance
- Embedding-based precision > 0.7 @ recall 0.6 on curated test set
- Latency stays <300ms p95 (hook SLO from ADR-029b)
- Graceful fallback to Jaccard if sentence-transformers not installed
- `REINVENTION_PHASE_B=2` env flag activates beta; old Jaccard still at `=1`

## Effort
~1 session (Backend Architect sonnet + 1h to install deps + benchmark).

## Dependencies
- ADR-029b (Phase B-alpha, shipped) — baseline
- Requires sentence-transformers dep added to pyproject.toml
