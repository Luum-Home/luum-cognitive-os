---
adr: 52
title: Provider Benchmark Harness
status: implemented
implementation_files:
  - docs/benchmarks/provider-quality-smoke.yaml
  - scripts/benchmark-providers
  - scripts/benchmark_providers.py
  - tests/unit/test_provider_benchmark_and_optimizer.py
---

# ADR-052 — Provider Benchmark Harness

## Status

**Implemented for the no-cost offline harness scope.** The repository now ships a
fixture-backed benchmark runner, a smoke task set, JSON/JSONL result output, and
unit coverage. Real provider invocations and LLM-as-judge scoring remain
explicit opt-in future adapter work so the harness can be validated without
spending tokens or depending on network availability.

## Context

Decisions about provider quality today are based on:
- Published benchmarks (SWE-bench, Terminal-Bench) that test providers
  against generic workloads, not OUR workload
- Anecdotal observation in single sessions
- Cost comparisons (quantitative but not quality-linked)

What we lack: **systematic evidence that Qwen produces comparable output
quality to Claude for the tasks WE actually dispatch**. The single live
smoke test in `scripts/smoke-qwen-fallback.sh` verifies mechanics, not
quality.

Before we can confidently route skills based on quality (ADR-050) or
auto-tune cascades (ADR-053), we need a benchmark harness that compares
providers on real tasks.

## Decision

**Implemented** as an offline benchmark tool with a provider-adapter boundary:

### Proposed tool

`scripts/benchmark_providers.py`:

```bash
python3 scripts/benchmark_providers.py \
  --task-set docs/benchmarks/provider-quality-smoke.yaml \
  --providers qwen,claude \
  --runs 3 \
  --judge claude   # use Claude to rate Qwen's outputs (LLM-as-judge)
```

Output: per-provider quality score, cost, latency, and per-task details as JSON; optional JSONL output is append-compatible with metric pipelines.

### Task sets

Curated YAML files per skill category can extend the shipped smoke set:
- `docs/benchmarks/provider-quality-smoke.yaml` — architectural reasoning
- `docs/benchmarks/code-implementation-tasks.yaml` — write function X
- `docs/benchmarks/classification-tasks.yaml` — tag/label prompts
- `docs/benchmarks/summarization-tasks.yaml` — compress N lines

Each task has: prompt, expected-properties (checklist the judge verifies),
ground truth (optional for automated eval).

### Judge model

The implemented harness uses deterministic expected-keyword checks for the no-cost baseline. For subjective tasks (design quality, prose clarity), a future adapter can use LLM-as-judge:
- Run same prompt through each provider
- Blind-label outputs
- Ask judge: "Which response is better on [criteria]?"
- Track win-rates

For objective tasks (code compiles, passes tests), use programmatic eval:
- Dispatch to each provider
- Compile/execute output
- Measure pass rate

### Metrics emitted

```json
{
  "benchmark_id": "...",
  "task_set": "sdd-design-tasks",
  "provider": "qwen",
  "model": "qwen3.6-plus",
  "tasks_total": 20,
  "tasks_passed": 17,
  "judge_win_rate_vs_claude": 0.45,
  "avg_cost_usd": 0.003,
  "avg_latency_ms": 2100,
  "p95_latency_ms": 3800
}
```

Optionally appended to `.cognitive-os/metrics/benchmark-results.jsonl` or another operator-selected JSONL path — feeds ADR-053 auto-optimizer proposals.

## Consequences

### Positive

- Quality comparisons become evidence-based, not anecdotal
- Regression detection: benchmark after every major model/config change
- Per-skill routing (ADR-050) gets real data instead of guesses
- Auto-optimizer (ADR-053) has a training signal

### Negative

- Real-provider benchmark runs cost real money (N prompts × M providers × K runs =
  nontrivial cost); the shipped fixture providers avoid that cost for CI smoke tests
- Judge bias: LLM judges have their own preferences (may favor own-family)
- Curation work: task sets need periodic refresh to match real workload

### Neutral

- Ensemble-dispatch path in `scripts/orchestrator.py` (currently `--ensemble`
  is a reserved flag only) could reuse benchmark infrastructure

## Dependencies

- No-cost fixture provider baseline — done
- ADR-049 stable (cascade mechanics solid) — done
- ADR-051 Phase 1+ (for multi-step task benchmarks) — done (Phase 1)
- Real provider adapters — future opt-in extension, not required for the implemented contract

## Related

- ADR-049 — cascade mechanics
- ADR-050 — per-skill routing (consumer of benchmark data)
- ADR-051 — agent loop (tool-use tasks need it)
- ADR-053 — auto-optimizer (the ultimate consumer)
- `lib/dispatch.py` — instrumented; benchmark reuses metrics schema
- `docs/benchmarks/provider-quality-smoke.yaml` — shipped smoke task set

## Open questions

1. Judge model choice: same family as tested provider (biased) or
   different (potentially unfair)? Probably different + rotate.
2. Task set ownership: who curates? Needs a maintainer or it rots.
3. Frequency: run on every commit (expensive) vs weekly (stale) vs
   on-demand (unused)?
4. Confidence intervals: N=3 runs per task is minimum. Higher = more
   cost. Is variance reproducible enough to trust N=3?

Implemented for the deterministic offline scope. Broader curated task sets, real provider adapters, and subjective judge rotation remain future research/operations work rather than missing core implementation.
