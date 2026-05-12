---
adr: 14
title: SDD Fast Path -- Skip Phases for Capable Models
status: accepted
implementation_status: partial
date: '2026-03-31'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit partial/phase scope
partial_remaining: Runtime model-capability auto-calibration remains partial; the pipeline uses configurable thresholds rather than automatically calibrated fast/full-path selection.
remaining_in_scope: true
partial_remaining_basis: manual correction after heuristic review
---

# ADR-014: SDD Fast Path -- Skip Phases for Capable Models

**Date:** 2026-03-31
**Status:** Accepted
**Commits:** e5552d1, 389628c, a866fdb
**Engram IDs:** 2026, 2028

## Context

Spec-Driven Development (SDD) followed a fixed 8-phase pipeline: explore, propose, spec, design, tasks, apply, verify, archive. Analysis of Anthropic's own framework findings (March 2026) revealed that with Opus 4.5/4.6, detailed planning (BMAD-style specs, task sharding) is overhead rather than assistance. A single error in micro-plans cascades through the pipeline. Anthropic's experiments showed that all an agent harness truly needs is agents for planning, generation, and evaluation -- the rest is dead weight for capable models. Additionally, context anxiety is not an issue with Opus 4.6's 1M token window.

## Decision

Implement a model-dependent SDD pipeline with a fast path for capable models:

- **Opus 4.6+** (fast path): explore, propose, apply, verify, archive. Skips spec, design, and tasks phases entirely.
- **Sonnet** (full path): All 8 phases. Still benefits from detailed specs and task breakdowns.
- **Haiku** (full path + extra guidance): All 8 phases with additional scaffolding.

Configuration lives in `cognitive-os.yaml` under `sdd.fast_path`:
- `enabled: true` (default)
- `model_threshold: opus` (minimum model tier for fast path)

Implementation in `lib/sdd_pipeline.py` uses the `_ANTHROPIC_CHAIN` ordering from model_catalog for tier comparison. Non-Anthropic models (GPT-4o, Gemini) never get fast path since they are not in the tier chain.

The most critical Anthropic finding preserved: the evaluator (verify phase) must ALWAYS be separate from the generator (apply phase). This separation is maintained in both fast and full paths.

## Alternatives Considered

- **Keep full pipeline for all models**: Consistent behavior regardless of model. Rejected because the overhead measurably slows Opus, and Anthropic's own data showed cascading errors from over-specified plans.
- **Auto-detect model capability at runtime**: Let the pipeline dynamically decide. Partially adopted -- the pipeline checks model tier at runtime, but the threshold is configurable rather than auto-calibrated.
- **Remove spec/design/tasks entirely**: Simplify the pipeline to just apply+verify. Rejected because Sonnet and Haiku demonstrably benefit from the structured phases.
- **Let the model choose its own path**: Ask the model whether it needs detailed specs. Rejected because this adds an LLM call to decide and the model has no reliable self-assessment of planning needs.

## Consequences

- Opus-driven SDD changes complete faster (skip 3 phases of planning overhead).
- The orchestrator rules in CLAUDE.md were updated to route model selection: Opus for architecture/debug, Sonnet for implementation.
- Parallel spec/design execution was also enabled in `cognitive-os.yaml` for the full path, further reducing total pipeline time.
- The agent efficiency strategy (ADR-016) was built on top of this, treating fast path as Level 0 of cost reduction.
