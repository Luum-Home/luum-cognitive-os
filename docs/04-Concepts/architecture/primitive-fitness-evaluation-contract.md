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
| Consumer evidence | `cos-export-consumer-improvement-proposals`, imported proposal bundles | Downstream evidence can support prioritization and provenance, but cannot promote a primitive by itself. |
| Portability/readiness | `cos-deps-install --json`, ADR-168 dependency reports | Candidate should not make cross-device installation or credential-safe setup less reproducible. |

Missing metric families are not treated as zero. They are excluded from the
weighted score and reported as `missing_signals`, making low-evidence promotion
visible instead of silently punitive. Consumer evidence and portability/readiness
are supporting domains: they can move the fitness score when core runtime metrics
exist, but a report built only from supporting evidence returns
`needs_evidence`.

## Promotion rule

A candidate is promotable only when:

1. candidate overall score is at least `required_delta` above baseline;
2. baseline and candidate both have enough sample evidence;
3. safety regressions are empty;
4. at least one core promotion domain is present for both baseline and candidate;
5. governed self-improvement promotion still has explicit approval.

Human approval remains necessary but is no longer sufficient.

## CLI contract

Generate a report:

```bash
scripts/cos-primitive-fitness \
  --primitive skills/example \
  --baseline-metrics /path/to/baseline/.cognitive-os/metrics \
  --candidate-metrics /path/to/candidate/.cognitive-os/metrics \
  --candidate-consumer-proposals /path/to/consumer-proposals.json \
  --candidate-dependency-report /path/to/cos-deps-install.json \
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


## Consumer and dependency evidence boundaries

The fitness layer may ingest consumer proposal bundles produced by
`scripts/cos-export-consumer-improvement-proposals` and dependency readiness
reports produced by `scripts/cos-deps-install.sh --json`. These are deliberately
not equivalent to proof that a primitive is better:

- consumer proposals are provenance-carrying requests or downstream signals; they
  stay propose-only and must have `runtime_effect: none`;
- `upstream-candidate` proposals increase supporting evidence, while
  `project-local` and `harness-gap` proposals remain visible as gaps;
- dependency readiness measures whether the candidate preserves ADR-168
  cross-device setup and credential-safe reporting;
- neither source can bypass core runtime metrics, safety checks, comparative
  evaluation, or explicit approval.

This keeps the Obsidian/Engram/consumer graph useful for audit and discovery
without turning downstream text or generated vault notes into a promotion oracle.


## Aggregate visibility through ledger and ACC

Individual fitness reports are candidate-specific. For session handoffs, weekly
reviews, and ACC, the SO also maintains a family-level ledger:

```bash
scripts/cos-primitive-fitness-ledger --project-dir .
```

The ledger scans primitive fitness report JSON files from:

- `docs/reports/primitive-fitness/*.json`
- `.cognitive-os/reports/primitive-fitness/*.json`
- `.cognitive-os/metrics/primitive-fitness-reports/*.json`

and writes:

- `docs/reports/primitive-fitness-ledger-latest.json`
- `docs/reports/primitive-fitness-ledger-latest.md`

It groups verdicts by primitive family (`hooks`, `skills`, `scripts`, `rules`,
`other`) and maps them into ACC statuses: `promote → aligned`,
`keep_draft → partial`, `needs_evidence → unverified`, and `reject → stale`.
The ACC pipeline loads this ledger as the `primitive_fitness_ledger` adapter and
adds lightweight capability rows with findings for rejected or under-evidenced
fitness reports.

This connection is intentionally visibility-only: ACC can surface stale or
under-evidenced primitive fitness, but promotion still happens only through the
governed promotion flow.

## Obsidian relationship

Obsidian should visualize this chain after evidence becomes durable memory or a
curated export artifact. It must not decide promotion. The evaluator is the
operational judge; Obsidian is a graph/audit surface for humans.

## Verification

```bash
python3 -m pytest tests/unit/test_primitive_fitness.py tests/behavior/test_primitive_fitness_cli.py -q
python3 -m pytest tests/unit/test_governed_self_improvement.py tests/behavior/test_governed_self_improvement_cli.py -q
```
