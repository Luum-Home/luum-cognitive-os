---
adr: 331
title: Graphify Portable Context Optimization Primitive
status: accepted
implementation_status: partial
date: '2026-05-22'
supersedes: []
superseded_by: null
extends:
- ADR-329
- ADR-320
implementation_files:
- .graphifyignore
- .gitignore
- scripts/cos-graphify-build
- scripts/cos-graphify-context-replay-benchmark
- scripts/cos-graphify-phase-d-semantic
- scripts/cos-graphify-hotspot-report
- scripts/cos-graphify-preload-matrix
- scripts/cos-graphify-token-footprint
- scripts/cos-graphify-token-reduction-smoke
- scripts/cos-graphify-run-telemetry
- tests/unit/test_cos_graphify_build.py
- tests/unit/test_cos_graphify_context_replay_benchmark.py
- tests/unit/test_cos_graphify_phase_d_semantic.py
- tests/unit/test_cos_graphify_preload_matrix.py
- tests/unit/test_cos_graphify_token_footprint.py
- tests/unit/test_cos_graphify_token_reduction_smoke.py
- tests/unit/test_cos_graphify_run_telemetry.py
- skills/graphify-query/SKILL.md
- docs/04-Concepts/architecture/graphify-portable-optimization-plan-2026-05-22.md
- docs/04-Concepts/architecture/graphify-phase-d-semantic-plan-2026-05-22.md
- docs/04-Concepts/architecture/graphify-real-token-telemetry-tooling-audit-2026-05-22.md
- docs/04-Concepts/architecture/graphify-integration-assessment-2026-05-22.md
- docs/09-Quality/manual-tests/graphify-controlled-trial.md
- docs/06-Daily/reports/graphify-controlled-trial-receipt-2026-05-22.md
- docs/06-Daily/reports/graphify-phase-b-sliced-receipt-2026-05-22.md
- docs/06-Daily/reports/graphify-phase-c-hotspot-report-2026-05-22.md
- docs/06-Daily/reports/graphify-phase-c1-optimization-targets-2026-05-22.md
- docs/06-Daily/reports/graphify-run-telemetry-real-paired-2026-05-22.md
- docs/06-Daily/reports/graphify-phase-d-execution-receipt-2026-05-22.md
tier: maintainer
classification_basis: Partial implementation because the primitive shell, code-sliced Phase B baseline, Phase C hotspot reporting, Phase C.1 optimization targets, preload selector, token-footprint estimator, real-session telemetry joiner, controlled token-reduction smoke, real-context replay benchmark, Phase D semantic execution wrapper, and Phase D backend receipt are implemented while remaining environment-dependent work covers rerunning semantic extraction after a backend is available, Codex TokenUsage normalization, and IDE or CLI projection beyond the maintainer skill.
tags:
- graphify
- context-optimization
- agentic-primitives
- primitive-projection
- multi-ide
- external-tool-adapter
verification_level: medium
---
# ADR-331 — Graphify Portable Context Optimization Primitive

## Status

Accepted with partial implementation.

## Context

Cognitive OS is authored as portable agentic primitives that are projected into
IDEs, CLIs, and harnesses. A tool that improves context selection must therefore
enter the OS as an owned primitive, not as a direct persistent installation into a
single IDE.

The 2026-05-22 Graphify investigation found that `safishamsi/graphify` is MIT
licensed, installable as `graphifyy`, and can build a useful code graph for
`lib/`. The focused upstream test suite passed, and a local `lib/` graph produced
7,956 nodes, 12,984 edges, and about 101x reported token-reduction economics.
Symbol-centered commands such as `explain`, `path`, and `affected` were useful for
maintainer navigation. Broad natural-language `query` was less reliable and should
remain secondary.

The same investigation also found that upstream Codex integration mutates local
instruction and hook files. That is not the right adoption path for this project
because the OS needs a canonical primitive that can later be projected into Codex,
Claude Code, and generic CLI surfaces with explicit support levels.

## Decision

Adopt Graphify as a maintainer-only context optimization primitive in controlled
phases.

Cognitive OS will:

1. keep Graphify output ignored by default;
2. use `scripts/cos-graphify-build` as the canonical build/update wrapper;
3. expose usage through `skills/graphify-query/SKILL.md`;
4. forbid upstream `graphify codex install`, hook installers, and platform
   installers in the normal workflow;
5. treat Graphify output as navigation evidence, not proof;
6. require explicit approval before semantic documentation extraction or other
   large token-budget operations;
7. join Graphify preload decisions with real session telemetry through
   `scripts/cos-graphify-run-telemetry` before making before/after token claims;
8. project the primitive through existing skill/catalog/projection mechanisms for
   each IDE or CLI.

## Consequences

Positive:

- Maintainers get cheaper graph-backed context selection for code relationships.
- Adoption remains portable across IDE and CLI surfaces.
- Generated graph artifacts do not pollute the repository by default.
- The OS can later add richer projection or hook behavior without inheriting
  upstream installer assumptions.

Negative:

- Graphify is not a full-repository optimizer by itself; it needs scoped queries,
  source confirmation, and tests.
- Semantic documentation extraction has meaningful token cost and remains gated.
- The first implementation is advisory/executable for maintainers, not automatic
  lifecycle enforcement.
- Real token reduction claims need comparable before/after runs; the telemetry
  joiner labels single-run evidence as non-causal.

## Alternatives rejected

- Direct upstream IDE installation was rejected because it mutates one IDE surface outside the OS projection model.
- No adoption was rejected because the local trial showed enough navigation and context-reduction value for a controlled wrapper.
- Immediate semantic indexing of all docs, ADRs, rules, and skills was deferred because the token cost belongs behind an explicit budget gate.

### Direct upstream IDE installation

Rejected. It optimizes one tool surface at a time and mutates persistent IDE state
outside the Cognitive OS primitive projection model.

### No adoption

Rejected. The local trial showed enough value for maintainer navigation and context
reduction to justify a controlled wrapper and skill.

### Immediate semantic indexing of all docs, ADRs, rules, and skills

Deferred. The estimated first corpus was about 1,012,740 tokens before iterative
updates. That belongs behind an explicit budget gate.

## Implementation Phases

The phases are defined in
`docs/04-Concepts/architecture/graphify-portable-optimization-plan-2026-05-22.md`:

1. primitive shell;
2. curated code graph baseline;
3. hotspot and impact audit;
4. optional semantic documentation slices;
5. real-session telemetry comparison;
6. IDE and CLI projection.

## Acceptance Criteria

1. `scripts/cos-graphify-build` can dry-run with repository exclusions visible.
2. `skills/graphify-query/SKILL.md` documents command selection, freshness checks,
   and the prohibition on upstream IDE/hook installers.
3. `graphify-out/` is ignored by Git.
4. Documentation links from the entrypoint MOC to the plan, ADR, investigation,
   manual test, and receipt.
5. Graphify-derived recommendations are labeled as navigation support and verified
   with source inspection or tests before implementation.
6. `scripts/cos-graphify-run-telemetry` reports bundles, preload files, estimated
   preload tokens, real session tokens, tools, duration, models, subagents, and
   a clear actual/estimated/mixed metric label.
7. Latest-session discovery requires explicit `--latest-claude-session`; otherwise
   operators must pass `--session`.
8. `scripts/cos-graphify-token-reduction-smoke` proves the causal-measurement
   harness with controlled paired fixtures before live model experiments are run.
9. `scripts/cos-graphify-context-replay-benchmark` simulates a controlled run
   with real repository file content and excludes generated caches/artifacts from
   broad baselines.

## Verification

The current partial implementation is verified by targeted unit tests and smoke
wrappers for the Graphify primitive shell, preload/token tooling, telemetry
joiner, and Phase D semantic wrapper.

```bash
python3 -m pytest \
  tests/unit/test_cos_graphify_build.py \
  tests/unit/test_cos_graphify_context_replay_benchmark.py \
  tests/unit/test_cos_graphify_phase_d_semantic.py \
  tests/unit/test_cos_graphify_preload_matrix.py \
  tests/unit/test_cos_graphify_token_footprint.py \
  tests/unit/test_cos_graphify_token_reduction_smoke.py \
  tests/unit/test_cos_graphify_run_telemetry.py -q
```

These tests prove wrapper command construction, generated report shape, budget
gating, telemetry joins, and deterministic replay behavior. They do not prove
production token savings or always-on IDE projection; those remain in the
partial implementation scope above.

