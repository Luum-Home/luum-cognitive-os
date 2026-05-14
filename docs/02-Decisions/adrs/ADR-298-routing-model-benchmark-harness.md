---
adr: 298
title: Reproducible Routing-Model Benchmark Harness
status: accepted
implementation_status: implemented
date: '2026-05-13'
supersedes: []
superseded_by: null
extends:
  - ADR-006
  - ADR-296
  - ADR-297
implementation_files:
  - lib/routing_benchmark.py
  - manifests/routing-benchmark-models.yaml
  - manifests/routing-benchmark-corpus.yaml
  - scripts/cos-routing-benchmark
  - tests/unit/test_routing_benchmark.py
tier: core
tags:
  - skill-router
  - benchmark
  - model-selection
  - reproducibility
  - license-policy
verification_level: medium
classification_basis: |
  Lands a benchmark harness (lib/routing_benchmark.py) plus seed manifests
  for candidate models and a 10-skill multilingual corpus. The harness
  gates every model on the project license policy (MIT/BSD/Apache) before
  any download, measures precision@1/@5/MRR per language plus
  latency/memory/size, and writes a versioned Markdown+JSON report.
  Tests run unconditionally against an injected stub adapter; a separate
  @pytest.mark.benchmark test exercises the real fastembed model.
---

# ADR-298: Reproducible Routing-Model Benchmark Harness

## Status

Accepted — 2026-05-13.

## Context

ADR-296 introduced a multilingual bi-encoder (FastEmbed +
`paraphrase-multilingual-MiniLM-L12-v2`) behind the regex skill router.
ADR-297 added an LLM tie-breaker for ambiguous cases. Both shipped with
tests, but the **choice of model was driven by a survey of upstream
benchmarks**, not by measurements on this project's corpus.

The operator correctly pointed out: "you can't choose models without
local benchmarks on my corpus." A model that scores 78%/82% on MIRACL
can underperform on a project whose skills are short, terse, and
heavily multilingual in ways the upstream eval set does not represent.

We need a single, reproducible artifact that any future model-selection
ADR can cite. Without one, model swaps become opinion fights.

## Decision

Adopt a **routing-model benchmark harness** (`lib/routing_benchmark.py`)
as the canonical tool for evaluating candidate routing models.

**Contract:** any future ADR that proposes adopting, replacing, or
tuning a routing model (bi-encoder, cross-encoder reranker, LLM, or
hybrid) MUST cite a report produced by this harness as evidence. The
report path goes in the ADR's `implementation_files` (for the harness
output) or in a dedicated evidence section.

### Surface

- `manifests/routing-benchmark-models.yaml` — candidate manifest;
  each entry declares `adapter`, `model_name`, `license`, `role`.
- `manifests/routing-benchmark-corpus.yaml` — multilingual seed
  corpus (10 skills × 6 languages × ~5 prompts each). Operators
  regenerate the full 385-skill corpus on demand via
  `scripts/cos-routing-benchmark --regenerate-corpus`, which uses
  ADR-049 LLM dispatch.
- `lib/routing_benchmark.py` — `BenchmarkHarness.run()` + adapters.
- `scripts/cos-routing-benchmark` — bash wrapper (canonical `.venv`).

### Metrics

Per model: precision@1, precision@5, MRR (with per-language
breakdown); cold-start, warm p50/p95/p99; peak RSS; on-disk size;
license-gate pass/fail; failure count. Output: Markdown table +
recommendation block + JSON twin (schema-versioned).

### License gate (ADR-006)

`license_is_permitted()` accepts only MIT, BSD (any variant), or Apache.
Any manifest entry declaring a non-permitted license (AGPL, SSPL, BSL,
CC-BY-NC, …) is refused **before** any download or model load. Under
`--strict` this is a hard exit (code 2); without it the model is
marked unloaded in the report and the run continues.

### Reproducibility

- Corpus is sorted by skill name; queries flattened deterministically.
- Each `(model_id, corpus_signature)` pair caches its measurements to
  `.cognitive-os/cache/routing-benchmark/`. Re-runs of unchanged
  inputs are cheap.
- Cold-start latency is measured from before `.load()` through the
  first `predict()` so catalog encoding is included.
- RSS uses `resource.getrusage(RUSAGE_SELF).ru_maxrss` with platform
  unit normalisation (macOS bytes vs. Linux KB).

### Adapter pattern

Models speak through `RoutingAdapter` (`load` / `predict` / `unload`).
Shipped adapter: `fastembed-bi-encoder`. Future adapters
(`onnx-cross-encoder`, `llm-rerank`, …) drop into the same registry
without modifying the harness core.

## Consequences

**Positive**

- Every model swap is grounded in numbers measured on *our* skills,
  *our* languages, *our* machine.
- The license gate prevents accidentally adopting AGPL/SSPL weights
  during exploratory work.
- The cache makes routine "did the corpus change?" checks fast.
- Tests run without network access via a stub adapter; the live
  fastembed test is opt-in via the `benchmark` marker.

**Negative / known limits**

- The 10-skill seed corpus is intentionally small. Full coverage
  requires the `--regenerate-corpus` flow, which costs LLM tokens.
  Treat the auto-generated prompts as a *baseline*, not gospel —
  manual refinement is expected before high-stakes ADR decisions.
- Latency numbers are local to the operator's machine. Cross-host
  comparisons require pinning the same environment snapshot
  (captured in the report header).
- RSS peaks are coarse — `ru_maxrss` does not isolate the model
  from the Python interpreter or fastembed runtime overhead.

## Verification

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_routing_benchmark.py -v
scripts/cos-routing-benchmark --quick --models baseline-minilm
```

The first command must pass all stub-backed tests unconditionally.
The second produces both `.md` and `.json` artefacts in
`docs/06-Daily/reports/` and exits 0.

A `--models <id>` invocation against an entry with a non-permitted
license must exit with code 2 under `--strict` (license-gate test).

## Related

- ADR-006 — license policy (MIT/BSD/Apache allow-list).
- ADR-049 — LLM dispatch (used by corpus regenerator).
- ADR-208 — dependency-adoption gate (no new deps were needed; the
  harness reuses the fastembed pin from ADR-296).
- ADR-296 — bi-encoder semantic matcher.
- ADR-297 — LLM tie-breaker for ambiguous routing.

## Evidence

Tier claim evidence is maintained through the boring-reliability control-plane lane:

```bash
scripts/cos-boring-reliability --json
scripts/cos-tier-claim-audit --json
```

This ADR remains `tier: core` because it affects default routing, observability,
or primitive-governance behavior that is part of the core operator control
plane. The tier claim is re-audited by `scripts/cos-tier-claim-audit`.
