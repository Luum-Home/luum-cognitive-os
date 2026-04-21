# ADR-052 — Provider Benchmark Harness

## Status

**Reserved** — stub. Blocked on having ≥3 providers wired (today: Qwen
+ Claude = 2). Not scheduled.

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

**Deferred**. Reserve the design for an offline benchmark tool:

### Proposed tool

`scripts/benchmark-providers.py`:

```bash
python3 scripts/benchmark-providers.py \
  --task-set docs/benchmarks/sdd-design-tasks.yaml \
  --providers qwen,claude \
  --runs 3 \
  --judge claude   # use Claude to rate Qwen's outputs (LLM-as-judge)
```

Output: per-provider quality score, cost, latency — CSV + markdown
report.

### Task sets

Curated YAML files per skill category:
- `docs/benchmarks/sdd-design-tasks.yaml` — architectural reasoning
- `docs/benchmarks/code-implementation-tasks.yaml` — write function X
- `docs/benchmarks/classification-tasks.yaml` — tag/label prompts
- `docs/benchmarks/summarization-tasks.yaml` — compress N lines

Each task has: prompt, expected-properties (checklist the judge verifies),
ground truth (optional for automated eval).

### Judge model

For subjective tasks (design quality, prose clarity), use LLM-as-judge:
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

Appended to `.cognitive-os/metrics/benchmark-results.jsonl` — feeds
ADR-053 auto-optimizer.

## Consequences

### Positive

- Quality comparisons become evidence-based, not anecdotal
- Regression detection: benchmark after every major model/config change
- Per-skill routing (ADR-050) gets real data instead of guesses
- Auto-optimizer (ADR-053) has a training signal

### Negative

- Benchmark runs cost real money (N prompts × M providers × K runs =
  nontrivial cost)
- Judge bias: LLM judges have their own preferences (may favor own-family)
- Curation work: task sets need periodic refresh to match real workload

### Neutral

- Ensemble-dispatch path in `scripts/orchestrator.py` (currently `--ensemble`
  is a reserved flag only) could reuse benchmark infrastructure

## Dependencies

- At least 3 providers wired (Qwen + Claude + one more) — today: 2
- ADR-049 stable (cascade mechanics solid) — done
- ADR-051 Phase 1+ (for multi-step task benchmarks) — done (Phase 1)

## Related

- ADR-049 — cascade mechanics
- ADR-050 — per-skill routing (consumer of benchmark data)
- ADR-051 — agent loop (tool-use tasks need it)
- ADR-053 — auto-optimizer (the ultimate consumer)
- `lib/dispatch.py` — instrumented; benchmark reuses metrics schema
- `docs/benchmarks/` (reserved directory, not created yet)

## Open questions

1. Judge model choice: same family as tested provider (biased) or
   different (potentially unfair)? Probably different + rotate.
2. Task set ownership: who curates? Needs a maintainer or it rots.
3. Frequency: run on every commit (expensive) vs weekly (stale) vs
   on-demand (unused)?
4. Confidence intervals: N=3 runs per task is minimum. Higher = more
   cost. Is variance reproducible enough to trust N=3?

Not scheduled. Unblocks ADR-053 auto-optimizer when curation resources
are available.
