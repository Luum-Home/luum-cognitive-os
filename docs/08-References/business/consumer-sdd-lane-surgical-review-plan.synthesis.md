---
type: reference-synthesis
source: docs/08-References/business/consumer-sdd-lane-surgical-review-plan.md
provenance: "Turns a comparison against the external `betta-tech/harness-sdd` project into a surgical, phased review program to determine whether Cognitive OS's SDD capability already solves the consumer 'task from intent to verified completion' problem, or needs a smaller, more legible lane on top of what exists."
---

## What it is

A review-and-correction plan (not an implementation) for making Cognitive OS's Spec-Driven Development workflow legible to a first-time consumer project, without building a duplicate workflow engine. Explicitly scoped as "determine which existing surfaces already solve the problem" before writing any new code.

## Key mechanics

- **Current-state table**: maps existing SDD-related surfaces (SDD skills, EAS/`executable-acceptance-specification.md`, traceability checker, workflow YAMLs, ADR-014 fast path, product-zone demotions, cross-harness authoring rules) to an initial interpretation of each gap.
- **Ten surgical questions** posed in order (center of gravity, happy path, vocabulary, proportionality, spec durability, state memory, traceability gate, reviewer boundary, cross-harness projection, evidence path) — the plan mandates answering before implementing.
- **Seven review workstreams** (WS1-WS7): center-of-gravity inventory, consumer happy-path audit, SDD/EAS reconciliation, task-state adapter design (local JSON/Markdown before GitHub/Linear/Jira), traceability/reviewer gate design, cross-harness projection review, and a five-minute demo/proof path — each with named inspection targets, output artifacts, and `pytest`-backed acceptance criteria.
- **Work-class proportionality matrix**: Trivial (no SDD) → Small (existing tests) → Medium (lightweight requirements/design/tasks/review) → Large (SDD + EAS recommended/required) → Critical (SDD + EAS + human approval + audit trail). Explicitly flags tension with ADR-014's model-capability-only fast path.
- **Six-phase sequenced plan**: Phase 0 audit-only → Phase 1 ADR/contract → Phase 2 local filesystem proof → Phase 3 traceability/reviewer gate → Phase 4 cross-harness projection → Phase 5 product demo → Phase 6 external task adapters (GitHub/Linear/Jira, deferred until local mode proves out).
- **Non-goals** explicitly rule out reviving the tombstoned workflow engine, making dashboards/squads part of the proof path, or introducing external API dependencies before local mode works.
- Includes a self-scored `TRUST_REPORT: SCORE=84 STATUS=HIGH EVIDENCE=5 UNCERTAINTIES=2`, naming its own evidence basis and two open uncertainties (CLI shape validation, external-adapter timing).

## Relations & where used

Directly extends the SDD pipeline described in the CLAUDE.md-level "SDD Workflow" (dependency graph: proposal → spec → design → tasks → apply/verify → archive) and the fast-path/model-threshold logic in `lib/sdd_pipeline.py`. Its proportionality matrix mirrors the Adaptive Workflow complexity classes in `rules/RULES-COMPACT.md` §1. Shares its "avoid duplicate workflow engine" and "local before external adapters" discipline with `execution-discipline.md` §2 (Shared Logic Before Duplicate Logic).

## Status / caveats

This is a **plan, not a completed review** — six of seven "Findings To Verify" are explicitly labeled "hypotheses, not yet final decisions." No named file changes have been made yet; the plan itself states "The first implementation slice, if approved, is local-only." Readers should not treat any workstream's "initial interpretation" column as a settled architectural conclusion.
