---
type: reference-synthesis
source: docs/08-References/business/case-study.md
provenance: "Provides two concrete, reproducible case studies (an external fintech monolith decomposition and a self-applied ADR implementation sprint) as evidence that Cognitive OS delivers large multi-agent acceleration under real constraints, not just in theory."
---

## What it is

Two anonymized/self-applied case studies documenting large-scale, multi-agent Cognitive OS usage with before/after time estimates:

1. **Case Study 1**: a fintech platform's 170-endpoint Express.js/Java/NestJS monolith decomposed into 14+ Go microservices, rebranded, and given a full Cognitive OS install, in ~24 hours using 100+ agents (vs. a 9-15 month traditional estimate).
2. **Case Study 2** (2026-05-07): Cognitive OS "used Cognitive OS" to research, draft, and Slice-A-implement 14 ADRs (220-236, ADR-229 tombstone) replacing a broken pre-agent-stash mechanism, in ~36 hours wall-clock (vs. a 4-8 week traditional estimate for the implementation portion alone).

## Key mechanics

- Both studies present task-by-task tables: traditional estimate vs. actual time vs. agents used, rolling up to a totals table (agents launched, files created, tests written, acceleration factor).
- Case Study 1 totals: ~300x acceleration, 100+ agents, 1,500+ Go files, 700+ tests, 60+ documents.
- Case Study 2 totals: 14 ADRs, 15 `lib/` modules, 11 schema-versioned manifests, 20+ test files, 6 hooks, 52/52 Phase-1 tests passing in 3.82s, 14/14 guardrail checks passing.
- Case Study 2 emphasizes a **versioned evaluation contract** (`manifests/orchestration-research-evaluation.yaml`, "C1-C4" constraints) as the mechanism that makes speed auditable rather than "research-inflation."
- Both include a "Reproducibility" section with exact file paths and commands (`git log`, `scripts/validate_substrate_consumers.py`, pytest invocations) an operator can rerun.

## Relations & where used

Referenced by `executive-summary.md` ("Proven in Production" table cites Case Study 1's metrics directly) and by `durable-product-master-plan.md` Phase 5, which cites Case Study 2 as the closure evidence for the orchestration coverage gap. Case Study 2's manifest and checklist are cross-referenced from `docs/03-PoCs/research/orchestration-gaps/`.

## Status / caveats

**FLAGGED numeric inconsistency**: Case Study 1 states the monolith has "170+ endpoints" and separately reports "Endpoints migrated: 79+ (31% of the monolith, growing)." 79/170 ≈ 46%, not 31% — the percentage does not match the stated endpoint counts as written. Similarly, the Challenge section states "47 use-case domains" but the Totals table reports "Domains decomposed: 8+ of 46 (growing)" — 46 vs. 47 is a stated-count mismatch. Both are noted here as flags, not corrected, per synthesis instructions.

These case studies are self-reported, point-in-time acceleration claims from the producing team itself (not independently audited), and both are explicitly framed by the project's own `durable-product-master-plan.md` as risking "research-inflation" if not backed by a versioned, auditable contract — which Case Study 2 attempts to supply via the C1-C4 manifest, but Case Study 1 does not have an equivalent contract layer.
