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

Routing-quality changes must run:

```bash
scripts/cos-routing-quality-gate
```

The gate performs three checks:

1. `tests/audit/test_skill_routing_patterns_ascii.py` keeps `routing_patterns:`
   as an ASCII-only fast path.
2. `tests/audit/test_multilingual_corpus_schema.py` verifies the multilingual
   benchmark fixture schema without loading FastEmbed.
3. `lib.routing_benchmark --multilingual` ranks benchmark prompts against the
   full SKILL.md catalog and enforces minimum candidate count and precision.

`routing_intents` quality is also reported by `scripts/audit-routing-intents`.
It is advisory by default because many legacy skills still need richer intent
metadata.

## Defaults

- Minimum candidate skills: 100
- Minimum multilingual corpus prompts: 8
- Minimum precision@1: 0.80
- Minimum precision@5: 0.90
- Maximum model failures: 0

Raise these thresholds only after expanding the adversarial multilingual corpus.

## Contextual Trigger

Use this rule when changing skill routing, `routing_patterns`, `routing_intents`,
semantic routing, routing benchmarks, or multilingual benchmark corpus files.
