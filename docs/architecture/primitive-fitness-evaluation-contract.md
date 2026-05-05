# Primitive Fitness Evaluation Contract

## Purpose

Cognitive OS self-improvement must not promote agentic primitives because a
conversation, Key Learning, or single test says they are better. Promotion must
compare a candidate primitive against the current baseline using the OKR/KPI and
operational metrics the SO already produces.

This contract adds an explicit fitness layer between proposal and promotion:

```text
learning / recurring failure / proposal
→ draft primitive
→ primitive fitness report
→ governed promotion evaluation
→ approved promotion
```

## Existing metric families included

The first implementation intentionally reuses existing signals instead of
inventing a new product score:

| Domain | Existing source examples | Promotion role |
|---|---|---|
| Quality | `trust-scores.jsonl`, `lib/kpi_collector.py` quality composite | Candidate should improve or preserve answer quality. |
| Effectiveness | `skill-metrics.jsonl`, `llm-dispatch.jsonl`, recurring `error-learning.jsonl` | Candidate should increase success and reduce repeated failures. |
| Safety | `hallucinations.jsonl`, safety-gate metrics, bypass/failure records | Any safety regression blocks promotion. |
| Friction | hook outcome metrics via `lib/friction_telemetry.py` | Candidate should reduce noisy blocks, warnings, bypasses, and false positives. |
| Cost/latency | dispatch latency/cost, hook p95 latency | Candidate should not buy quality with uncontrolled cost or latency. |
| Dogfood/product fitness | `lib/dogfood_scorer.py` | Candidate should not weaken the SO's own product-health proof. |

Missing metric families are not treated as zero. They are excluded from the
weighted score and reported as `missing_signals`, making low-evidence promotion
visible instead of silently punitive.

## Promotion rule

A candidate is promotable only when:

1. candidate overall score is at least `required_delta` above baseline;
2. baseline and candidate both have enough sample evidence;
3. safety regressions are empty;
4. governed self-improvement promotion still has explicit approval.

Human approval remains necessary but is no longer sufficient.

## CLI contract

Generate a report:

```bash
scripts/cos-primitive-fitness \
  --primitive skills/example \
  --baseline-metrics /path/to/baseline/.cognitive-os/metrics \
  --candidate-metrics /path/to/candidate/.cognitive-os/metrics \
  --json
```

Feed it into governed self-improvement:

```bash
python3 scripts/cos_governed_self_improvement.py \
  --project-dir . \
  evaluate-from-fitness <draft-id> \
  --fitness-report primitive-fitness.json
```

The resulting promotion evaluation is still stored under the draft and appended
to `.cognitive-os/metrics/primitive-promotion-evaluations.jsonl`.

## Obsidian relationship

Obsidian should visualize this chain after evidence becomes durable memory or a
curated export artifact. It must not decide promotion. The evaluator is the
operational judge; Obsidian is a graph/audit surface for humans.

## Verification

```bash
python3 -m pytest tests/unit/test_primitive_fitness.py tests/behavior/test_primitive_fitness_cli.py -q
python3 -m pytest tests/unit/test_governed_self_improvement.py tests/behavior/test_governed_self_improvement_cli.py -q
```
