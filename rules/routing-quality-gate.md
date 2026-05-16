---
slug: routing-quality-gate
scope: validation
enforced_by: scripts/cos-routing-quality-gate
---

# Routing Quality Gate

## Purpose

Prevent false-green multilingual routing changes by validating prompts against
the full on-disk skill catalog, not only the small prompt corpus.

## Contract

Routing-quality changes must run the maximal local gate before merge:

```bash
scripts/cos-routing-max-gate
```

The max gate chains three layers:

1. `scripts/audit-routing-intents --fail-on-issues` verifies every `SKILL.md`
   has non-generic semantic routing intent text.
2. `scripts/cos-routing-corpus-audit` reports multilingual corpus coverage by
   skill, language, and uncovered user-facing skill surface.
3. `scripts/cos-routing-quality-gate --fail-on-top1-misses` runs the live
   semantic benchmark against the full SKILL.md catalog.

For cheaper iteration while editing, run layers individually:

```bash
scripts/audit-routing-intents --fail-on-issues
scripts/cos-routing-corpus-audit
scripts/cos-routing-quality-gate --fail-on-top1-misses
```

`lib.routing_benchmark --multilingual` now reports `min_top_2_margin`,
`avg_top_2_margin`, and low-margin correct hits. A pass with tiny top-2 margins
is not strong evidence of worldwide routing; it means the current corpus passed
but has near-neighbor risk that the corpus expansion SDD should cover.

## Defaults

- Minimum candidate skills: 100
- Minimum multilingual corpus prompts: 8
- Minimum precision@1: 0.80
- Minimum precision@5: 0.90
- Maximum model failures: 0
- Top-1 misses: allowed by `cos-routing-quality-gate`, forbidden by `cos-routing-max-gate`
- Minimum top-2 margin: 0.0 until the corpus is expanded enough to calibrate a safe floor

Raise these thresholds only after expanding the adversarial multilingual corpus.
Use environment variables for stricter local runs, for example:

```bash
COS_ROUTING_MIN_CORPUS_PROMPTS=40 \
COS_ROUTING_MIN_LANGUAGES=6 \
COS_ROUTING_MAX_LOW_MARGIN_HITS=0 \
scripts/cos-routing-max-gate /tmp/cos-routing-max-gate-strict
```

## Contextual Trigger

Use this rule when changing skill routing, `routing_patterns`, `routing_intents`,
semantic routing, routing benchmarks, or multilingual benchmark corpus files.
