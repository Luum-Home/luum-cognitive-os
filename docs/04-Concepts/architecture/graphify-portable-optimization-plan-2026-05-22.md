# Graphify Portable Optimization Plan — 2026-05-22

## Premise

Cognitive OS does not optimize one IDE at a time. It owns portable agentic
primitives and then projects them into IDEs, CLIs, and harnesses. Graphify can be
useful only if it is wrapped as an OS-owned context optimization primitive instead
of being installed as an upstream Codex or Claude add-on.

The primitive boundary is: Graphify helps agents select context, inspect dependency
paths, and estimate impact. It does not become the source of truth for correctness,
architecture, or governance.

## Decision Summary

Adopt Graphify in controlled phases:

1. keep generated graphs out of version control by default;
2. expose Graphify through a maintainer skill and wrapper script;
3. build curated code graphs first;
4. add semantic documentation extraction only after explicit budget approval;
5. project the resulting primitive through the normal Cognitive OS projection
   surfaces for each IDE or CLI.

## Phase A — Primitive Shell

Status: implemented.

Artifacts:

- `.graphifyignore` defines safe default exclusions for generated, cached,
  dependency, metric, and sensitive paths.
- `.gitignore` ignores `graphify-out/` outputs.
- `scripts/cos-graphify-build` wraps upstream Graphify with Cognitive OS defaults.
- `skills/graphify-query/SKILL.md` defines maintainer usage, command selection,
  and platform projection rules.
- `docs/02-Decisions/adrs/ADR-331-graphify-portable-context-optimization-primitive.md`
  records the durable architecture decision.

Acceptance criteria:

1. `scripts/cos-graphify-build --dry-run` shows repository exclusions before any
   expensive extraction.
2. The skill forbids upstream IDE/hook installers.
3. Generated `graphify-out/` directories are ignored by Git.

## Phase B — Curated Code Graph Baseline

Status: implemented for code-first slices.

Build Phase B with bounded, observable slices instead of one repository-root scan:

```bash
scripts/cos-graphify-build --phase-b --out /tmp/cos-graphify-phase-b --skip-benchmark --timeout-seconds 60 --progress-seconds 10
```


Execution note: an initial repository-root Phase B attempt on 2026-05-22 was stopped after no progress output for about 25 seconds. The wrapper now supports `--phase-b`, per-slice `--timeout-seconds`, per-slice `--progress-seconds`, skipped-empty receipts, and a summary JSON. The first sliced receipt is `docs/06-Daily/reports/graphify-phase-b-sliced-receipt-2026-05-22.md`.

The baseline should answer whether Graphify can usefully map relationships across:

- `lib/` runtime modules;
- `hooks/` shell hook entrypoints;
- `scripts/` maintainer utilities;
- `skills/` procedural primitives;
- `rules/` governance primitives;
- `packages/agent-service/` service code.

Acceptance criteria:

1. The build completes without indexing dependency caches, generated metrics, or
   known sensitive paths.
2. `graphify benchmark` reports useful context-reduction economics.
3. At least three symbol-centered queries produce actionable file or symbol hints.

## Phase C — Hotspot and Impact Audit

Status: implemented for Phase B code slices.

Use Graphify outputs to create a maintainer report, not automated rewrites. The
report should identify high-degree nodes, fragile dependency paths, and candidate
areas where repeated agent context loading can be reduced.

Report command:

```bash
scripts/cos-graphify-hotspot-report /tmp/cos-graphify-phase-b/cos-graphify-slices-summary.json --out docs/06-Daily/reports/graphify-phase-c-hotspot-report.md
```

The first report is `docs/06-Daily/reports/graphify-phase-c-hotspot-report-2026-05-22.md`. The first Phase C.1 optimization target report is `docs/06-Daily/reports/graphify-phase-c1-optimization-targets-2026-05-22.md`. The reusable preload selector is `scripts/cos-graphify-preload-matrix`, which can select bundles from explicit paths or from tracked changes and optional untracked files with `--changed --include-untracked`. The context-footprint estimator is `scripts/cos-graphify-token-footprint`.

Acceptance criteria:

1. The report separates extracted graph facts from maintainer inference.
2. Any optimization recommendation points to source files and verification tests.
3. No code is rewritten based only on graph output.

## Phase D — Optional Semantic Documentation Slices

Status: gated and planned in `docs/04-Concepts/architecture/graphify-phase-d-semantic-plan-2026-05-22.md`.

Documentation and ADRs are high value but token-expensive. The 2026-05-22 estimate
for the first semantic corpus was about 1,012,740 tokens across architecture docs,
ADRs, rules, and skills. That makes semantic extraction useful only as an explicit
budgeted operation.

Recommended slice order:

1. `docs/04-Concepts/architecture/` for architecture retrieval;
2. `docs/02-Decisions/adrs/` for decision retrieval;
3. `rules/` and `skills/` for governance and procedural routing.

Acceptance criteria:

1. The user approves backend and token budget before `--include-docs` is used.
2. Output is kept outside the repository or explicitly ignored.
3. Semantic answers cite documents and are labeled as retrieval support, not policy.

## Phase E — IDE and CLI Projection

Status: planned.

Graphify must be projected like any other Cognitive OS primitive. The canonical
source is the OS skill and wrapper. IDE-specific instructions can be generated or
adapted later, but they must not bypass the primitive boundary.

Projection rules:

- Codex: expose `/graphify-query` as a skill; do not rely on upstream additional
  context hooks.
- Claude Code: expose the same skill and wrapper through the skill catalog; any
  hook use must be OS-authored and separately accepted.
- Generic CLI: support manual execution through `scripts/cos-graphify-build` and
  raw `graphify` commands.

Acceptance criteria:

1. The same plan works when projected to Codex, Claude Code, or a generic CLI.
2. Platform differences are documented as support levels, not hidden assumptions.
3. No upstream installer mutates persistent IDE state as part of normal adoption.
