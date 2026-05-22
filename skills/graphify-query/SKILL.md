---
name: graphify-query
description: 'Use when a Cognitive OS maintainer asks to use Graphify, query or build a repository knowledge graph, inspect graph paths, explain graph nodes, run graph affected analysis, benchmark a Graphify graph, or use a graph to reduce repository context before planning; do not use for proof of correctness, security validation, or ordinary text search when no graph is needed.'
invoke: /graphify-query
tag: os-only
model: sonnet
audience: os-dev
effort: sonnet
summary_line: Maintainer workflow for Graphify-backed repository graph builds and context-selection queries.
version: 1.0.0
platforms:
- claude-code
- codex
- generic-cli
platform_support:
  generic-cli:
    support_level: executable
    evidence:
    - scripts/cos-graphify-build
    - graphify explain <symbol> --graph <graph.json>
    - graphify path <from-symbol> <to-symbol> --graph <graph.json>
prerequisites:
- graphifyy or uvx
routing_patterns:
- pattern: \bgraphify\b
  confidence: 0.95
- pattern: \bknowledge\s+graph\b
  confidence: 0.85
- pattern: \brepo(?:sitory)?[- ]?graph\b
  confidence: 0.85
- pattern: \bgraph\s+(query|path|affected|explain|benchmark)\b
  confidence: 0.85
routing_intents:
- intent: graphify_repository_graph_query
  description: User asks to query, build, inspect, benchmark, or use Graphify repository knowledge graphs for Cognitive OS maintainer context.
  confidence: 0.9
triggers:
- graphify
- /graphify-query
- knowledge graph
- repo graph
- graph query
- graph affected
- graph explain
---
<!-- SCOPE: os-only -->
# Graphify Query

## Purpose

Use Graphify as a maintainer-only context optimization primitive. It can reduce
repository-reading cost, reveal code relationships, and help choose files before a
change. It is not a correctness proof, security review, test substitute, or source
of architectural truth.

Cognitive OS owns the primitive and projects it to each IDE or CLI through the
normal skill/catalog/projection surfaces. Do not install upstream Graphify hooks or
persistent IDE instructions from this skill.

## Default Workflow

1. Identify the graph file.
   - Prefer an explicit user-provided graph path.
   - If none is provided, use `graphify-out/graph.json` when it exists.
   - If no graph exists and the task clearly needs one, build a scoped graph with
     `scripts/cos-graphify-build`.
2. Check freshness when the graph JSON exposes commit metadata.
   - Compare any `built_at_commit` value with `git rev-parse HEAD`.
   - If metadata is missing or the graph lives under `/tmp`, report that freshness
     is bounded by the build command and timestamp you observed.
3. Choose the narrowest Graphify command for the question.
4. Report the command, graph path, confidence, and any ambiguity. Keep test and
   source inspection as the final authority.

## Build and Update Rules

Use the repository wrapper instead of raw upstream installers:

```bash
scripts/cos-graphify-build lib --out /tmp/cos-graphify-lib --skip-benchmark
```

For a broader but still code-first baseline, use bounded Phase B slices instead
of a silent repository-root scan:

```bash
scripts/cos-graphify-build --phase-b --out /tmp/cos-graphify-phase-b --skip-benchmark --timeout-seconds 60 --progress-seconds 10
```

Rules:

- Do not run `graphify codex install`, `graphify hook install`, or
  `graphify install --platform ...` from this skill.
- Do not enable semantic documentation extraction unless the user explicitly
  approves the backend and token budget. Use `--include-docs` only after approval.
- Keep generated `graphify-out/` artifacts ignored unless a human explicitly asks
  to preserve a receipt or fixture.
- Treat `skills/` and `rules/` skipped-empty results in code-only mode as expected;
  they are Markdown-heavy governance surfaces and belong to semantic Phase D.
- Prefer temporary output roots under `/tmp` for investigations.


Generate a Phase C hotspot report from a Phase B summary:

```bash
scripts/cos-graphify-hotspot-report /tmp/cos-graphify-phase-b/cos-graphify-slices-summary.json --out docs/06-Daily/reports/graphify-phase-c-hotspot-report.md
```

## Command Selection

| Question | Command pattern | Notes |
|---|---|---|
| What does this symbol depend on? | `graphify explain <symbol> --graph <graph.json>` | Best first command for symbol-centered work. |
| How are two symbols connected? | `graphify path <from-symbol> <to-symbol> --graph <graph.json>` | Use exact class, function, or module names when possible. |
| What may be impacted? | `graphify affected <symbol> --depth 2 --graph <graph.json>` | Treat as impact hints, then verify with tests and code search. |
| Is the graph useful enough? | `graphify benchmark <graph.json>` | Report token-reduction figures as navigation economics only. |
| Broad natural-language search | `graphify query "question" --graph <graph.json>` | Use only after symbol commands fail or the question is exploratory. |

If the installed Graphify version uses a different flag spelling, run
`graphify <command> --help` and adapt without changing the skill.


## Preload Matrix

Before modifying code in a known Phase C.1 hotspot area, select the preload bundle
from changed paths, symbols, or topic hints:

```bash
scripts/cos-graphify-preload-matrix lib/harness_adapter/base.py hooks/destructive-git-blocker.sh
```

Use JSON when another tool or agent needs structured output:

```bash
scripts/cos-graphify-preload-matrix lib/harness_adapter/base.py --json
```

For the current Git worktree, select bundles from tracked changes and optionally
untracked files before planning edits:

```bash
scripts/cos-graphify-preload-matrix --changed --include-untracked --json
```


Current bundles:

| Trigger area | Preload focus | Confirmation surface |
|---|---|---|
| `lib/harness_adapter/`, `CanonicalEvent`, `lib/sprint_orchestrator.py` | Harness event contract and adapters | harness adapter, sprint orchestrator, and preamble integration tests |
| `lib/history_sanitization.py`, history rewrite scripts | History rewrite local toolchain | history sanitization unit, behavior, and ledger contract tests |
| `hooks/destructive-git-blocker.sh`, `hooks/_lib/` | Destructive Git blocker and hook libs | chaos tests plus `bash -n` |
| `scripts/cos_work_inventory.py`, `hooks/agent-prelaunch.sh` | Work inventory and prelaunch coordination | work inventory unit/audit/behavior/red-team tests |
| `packages/agent-service/`, `StoredSession`, session models | Agent-service session schema and store | agent-service contract, session, and health tests |

If no bundle matches, do not force Graphify. Use ordinary source inspection or
generate a fresh hotspot report for the relevant slice.


Estimate the context-footprint reduction of a selected preload bundle before
planning large changes:

```bash
scripts/cos-graphify-token-footprint --changed --include-untracked --json
```

This is a deterministic token proxy, not actual model billing telemetry. Use it
to compare broad slice reading against the preload bundle.

## Reporting Standard

Every answer using this skill should include:

- graph path used;
- Graphify command or wrapper command used;
- whether the result is directly extracted, inferred, or ambiguous;
- one verification step outside Graphify when the answer affects code changes.

Do not say the graph proves behavior. Say it suggests relationships that require
source and test confirmation.

## Contextual Trigger

Use this skill when the maintainer asks for Graphify, repository knowledge graphs,
context reduction, graph path/explain/affected/benchmark output, or graph-backed
planning for Cognitive OS primitive work.
