---
type: reference-synthesis
source: docs/08-References/business/cognitive-os-efficiency-operating-model.md
provenance: "Translates an informal social-media thesis about AI-coding efficiency (less lost context, fewer repeated decisions, lower token waste) into a concrete, evidence-gated Cognitive OS implementation roadmap so the claim can be built and measured rather than just asserted."
---

## What it is

A product/engineering roadmap that converts a marketing-adjacent thesis ("clear spec + specialized agents + live context + computable workflow state = organized engineering system, not a single chat") into six concrete COS mechanisms, a claim-tier ladder, a six-phase implementation roadmap, and a record of what has actually shipped as of 2026-06-15.

## Key mechanics

- **Core translation** into six first-class capabilities: clear work contract, persistent working memory, specialized agent roles, live context organization, computable loop state, evidence-backed claims.
- **Outcome map** table ties each desired outcome (less wasted context, fewer iterations, better code quality, etc.) to an existing COS mechanism, a missing/immature mechanism, and a named porting target (e.g., `cos-context-plan`, `cos-work-preflight`).
- **Product promise ladder**: four claim tiers (Structural / Directional / Measured / Product), each gated by increasingly strong evidence — from "installed primitives" up to "multiple task families, multiple stacks, repeated runs, real provider telemetry." Explicitly bans unproven claims like "saves 50% of every subscription" or "always reduces tokens."
- **Six-phase roadmap**: (1) make OS status computable (`cos status`), (2) reduce context before model calls (`cos-context-plan`), (3) make roles explicit (`cos-role-selection-report`), (4) strengthen quality evidence (TDD/review forecast), (5) unify installation UX (`cos doctor`), (6) prove post-level outcomes via `cos-so-impact-eval` paired benchmarks.
- **Implemented advisory slice (2026-06-15, ADR-339)**: a table mapping each roadmap item to a shipped script (`scripts/cos-status`, `scripts/cos-adapter-capabilities`, `scripts/cos-context-plan`, etc.), explicitly labeled "candidate/advisory lifecycle primitives... receipts and planning aids, not universal runtime enforcement yet."

## Relations & where used

Directly complements `workstation-container-comparison-report.md` (the `cos-so-impact-eval` benchmark family referenced here is the same measurement infrastructure) and shares the claim-discipline stance of `cos-vs-ai-slop-falsification.md`. Its "public messaging boundary" section is the operating-model analog of the guardrails also expressed in `durable-product-master-plan.md`.

## Status / caveats

This is a live roadmap with a mixed status: sections 1-6 describe target-state deliverables and acceptance criteria that are largely aspirational/planned, while the "Implemented advisory slice — 2026-06-15" section documents what has actually shipped, explicitly self-labeled as advisory rather than enforced. Readers should not conflate the roadmap language (phases 1-6) with the implemented-slice table — only the latter reflects current runtime behavior as of the document's own dating.
