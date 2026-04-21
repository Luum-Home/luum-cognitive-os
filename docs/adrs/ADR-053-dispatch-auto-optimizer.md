# ADR-053 — Dispatch Auto-Optimizer

## Status

**Reserved** — stub. Blocked on ADR-050 (per-skill routing) and ADR-052
(benchmark harness). Depends on several months of accumulated
`llm-dispatch.jsonl` metrics. Not scheduled.

## Context

ADR-049 introduced `--providers qwen,claude` — a static cascade. Every
skill, every task uses the same priority list. This works but is coarse:

- Some skills perform better on one provider than another (per ADR-052
  benchmarks, when they exist)
- Provider reliability varies over time (Qwen had an outage, Claude was
  rate-limited, DeepSeek added vision)
- Pricing changes (Z.AI doubled prices twice in Q1 2026)
- Our task distribution shifts (more code gen this week, more
  summarization next month)

A static cascade can't adapt to these. An **auto-optimizer** reads
accumulated metrics and re-tunes routing per skill/task type.

## Decision

**Deferred**. Reserve the design for a Python module that:

1. Reads `.cognitive-os/metrics/llm-dispatch.jsonl` (produced by C2
   of ADR-049)
2. Aggregates per `(skill_name, task_type)` tuple: success rate, cost,
   latency, provider choice
3. Identifies providers that under-perform on specific (skill,task)
   combinations
4. Emits a proposed routing update → written to a git-tracked
   `.cognitive-os/routing/auto-tuned.yaml`
5. Operator reviews and commits (or rejects) — NOT auto-applied

### Proposed API

```python
from lib.dispatch_optimizer import analyze, propose_routing

report = analyze(
    metrics_path=".cognitive-os/metrics/llm-dispatch.jsonl",
    window_days=30,
    min_samples_per_tuple=10,
)

# For each (skill, task_type) with enough data, propose optimal provider
proposals = propose_routing(report, cost_weight=0.3, quality_weight=0.7)

# Write proposal (git-tracked so diffs are reviewable)
write_proposal(proposals, path=".cognitive-os/routing/auto-tuned.yaml")
```

### Human-in-the-loop flow

1. Weekly cron: `python3 scripts/auto-tune-routing.py`
2. Proposal written to `.cognitive-os/routing/auto-tuned.yaml` (diff
   visible in `git status`)
3. Operator reviews diff. Reasonable changes → commit. Weird changes →
   investigate (may reveal metrics anomaly or provider regression).
4. On commit, `lib/dispatch.py` reads the tuned routing and applies it
   to matching `(skill, task)` calls.

### Cold start

Before any auto-tuning happens, need:
- ≥30 days of data in `llm-dispatch.jsonl`
- ≥10 samples per `(skill, task)` tuple being tuned
- ADR-050 schema so skills declare `task_type` consistently

Until those conditions hold: default cascade (ADR-049) is used; no
auto-tuning applies.

## Consequences

### Positive

- Routing adapts to our actual task distribution + provider realities
- Provider degradation detected as a shift in win-rate (early warning)
- Cost decreases over time as cheaper providers get tuned to tasks
  they're good at
- No orchestrator downtime — tuning is async, reviewed, applied on
  commit

### Negative

- Complex feedback loops: tuning based on past metrics + changes affect
  future metrics. Can oscillate if not damped.
- "Weird proposal" is hard to debug. Why did it move this skill from
  Claude to Qwen? The metrics may show Qwen was winning by 1% but the
  variance is 10%.
- Requires baseline quality metric (ADR-052 benchmarks or judge score
  in JSONL). Without quality signal, only cost+latency can be optimized
  — risks silently degrading quality.

### Neutral

- Operator retains veto (no auto-apply). Safety valve for all of the
  above concerns.

## Dependencies

- ADR-049 cascade + JSONL metrics — done
- ADR-050 skill routing schema — TODO
- ADR-052 benchmark harness — TODO (provides quality signal)
- 30+ days of production `llm-dispatch.jsonl` data — blocked on adoption

## Related

- ADR-049 — metric foundation
- ADR-050 — consumer of auto-tuned routing
- ADR-052 — quality signal producer
- `lib/dispatch.py` — reads tuned routing (future)
- `.cognitive-os/metrics/llm-dispatch.jsonl` — primary input
- `.cognitive-os/routing/auto-tuned.yaml` — reserved output path

## Open questions

1. **Quality metric without ADR-052**: can we use proxy signals
   (success rate, error recovery count, follow-up human edits) instead
   of benchmark scores? Easier to collect but noisier.
2. **Stability**: how to dampen oscillation? Moving averages? Minimum
   "confidence interval" to trigger proposals?
3. **Observation bias**: if we stop sending task X to provider Y
   because Y under-performed, we lose data about whether Y improved.
   Periodic exploration (e-greedy routing) would fix this but costs
   money.
4. **Operator fatigue**: how often should proposals be generated?
   Weekly could produce noisy churn. Monthly may lag real shifts.

Not scheduled. Explicitly a "when we have evidence, not on principle" ADR.
