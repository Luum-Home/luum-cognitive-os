# Graphify Controlled Trial Receipt — 2026-05-22

## Scope

This receipt validates the first controlled Graphify trial slice for Cognitive OS. The run intentionally used a bounded code-only target and did not install Graphify hooks or mutate assistant instructions.

## Commands

Syntax validation:

```bash
python3 -m py_compile scripts/cos-graphify-build
```

Dry run:

```bash
scripts/cos-graphify-build lib \
  --out /tmp/cos-graphify-phase-receipt \
  --graphify-bin /tmp/graphify-venv/bin/graphify \
  --dry-run
```

Graph build:

```bash
scripts/cos-graphify-build lib \
  --out /tmp/cos-graphify-phase-receipt \
  --graphify-bin /tmp/graphify-venv/bin/graphify \
  --skip-benchmark
```

Benchmark:

```bash
/tmp/graphify-venv/bin/graphify benchmark \
  /tmp/cos-graphify-phase-receipt/graphify-out/graph.json
```

Query smoke:

```bash
/tmp/graphify-venv/bin/graphify query \
  "Which modules handle memory and routing?" \
  --graph /tmp/cos-graphify-phase-receipt/graphify-out/graph.json \
  --budget 1200
```

## Evidence

The dry run reported:

```text
COS_GRAPHIFY_BUILD_MODE=code-only
COS_GRAPHIFY_TARGET=<repo-root>/lib
COS_GRAPHIFY_OUT=/private/tmp/cos-graphify-phase-receipt/graphify-out
COS_GRAPHIFY_IGNORE_PATTERNS=28
```

The build reported:

```text
[graphify extract] found 383 code, 0 docs, 0 papers, 0 images
[graphify] Deduplicated 309 node(s) (88 exact, 211 fuzzy).
[graphify extract] wrote /private/tmp/cos-graphify-phase-receipt/graphify-out/graph.json: 7956 nodes, 12984 edges, 513 communities
[graphify extract] wrote /private/tmp/cos-graphify-phase-receipt/graphify-out/.graphify_analysis.json
COS_GRAPHIFY_GRAPH=/private/tmp/cos-graphify-phase-receipt/graphify-out/graph.json
```

The benchmark reported:

```text
Corpus:          397,800 words -> ~530,400 tokens (naive)
Graph:           7,956 nodes, 12,984 edges
Avg query cost:  ~5,252 tokens
Reduction:       101.0x fewer tokens per query
```

The query smoke returned bounded graph context for memory/routing terms from the generated graph.

## Boundary Checks

- Graphify was invoked from an existing temporary venv at `/tmp/graphify-venv`; it was not vendored into the repository.
- The graph output was written under `/tmp/cos-graphify-phase-receipt`, not into the repository working tree.
- The wrapper ran in code-only mode, so no semantic LLM extraction was required.
- No Graphify hook install command was run.
- No Graphify Codex or assistant instruction install command was run.

## Result

`PASS`: The first controlled implementation slice is demonstrated for the bounded `lib/` graph: scoped ignore rules, wrapper execution, manual test documentation, receipt capture, benchmark evidence, and no hook/instruction mutation.

Remaining before broader adoption:

1. Decide whether to keep graph outputs external to the repo or add ignored local `graphify-out/` outputs.
2. Decide whether a maintainer-only Graphify query skill should be added.
3. Run a scoped documentation semantic extraction only if token budget and backend are explicitly approved.
