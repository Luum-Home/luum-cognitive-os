<!-- SCOPE: os-only -->
---
name: product-answer
description: "Use when the user asks a Cognitive OS product/commercial question such as differentiator, moat, wedge, ICP, pricing, competitors, pitch, positioning, or what claims are safe. Always prefer the cached ADR-282 product answer cards before reading broad docs."
version: 1.0.0
user-invocable: true
audience: os-dev
tags: [product, commercial, evidence, positioning, token-efficiency]
summary_line: "Answer COS product/commercial questions from cached evidence cards, not broad repo research."
platforms: ["claude-code", "codex", "shell"]
prerequisites: []
routing_patterns:
  - pattern: '\b(diferenciador|factor diferenciador|moat|wedge|positioning|posicionamiento)\b'
    confidence: 0.96
  - pattern: '\b(product|producto|commercial|comercial)\b.{0,40}\b(question|pregunta|answer|respuesta)\b'
    confidence: 0.90
  - pattern: '\b(ICP|buyer|pricing|precio|competitors|competencia|pitch|landing)\b'
    confidence: 0.86
  - pattern: '\b(what|qué|que).{0,30}(claim|prometer|diferencia|vende|vendemos)\b'
    confidence: 0.80
---

# Product Answer

## Purpose

Answer Cognitive OS product and commercial questions from the ADR-280/ADR-282
product-answer primitives instead of re-investigating the full SO documentation.

This is an **OS-only** skill. It is for Cognitive OS maintainers answering
questions about this SO's positioning, commercial story, claim safety, or product
wedge. It is not a project-facing adopter skill.

## Use when

- The user asks: "cuál es nuestro diferenciador?", "what is our moat/wedge?",
  "qué decimos de competidores?", "pricing", "ICP", "pitch", "landing".
- The user asks whether a product/commercial claim is safe.
- The user asks what primitives answer a product or commercial question.
- The answer should be short, evidence-backed, and token-efficient.

## Do not use when

- The user asks to edit product-answer code or manifests; use normal coding flow.
- The user asks for fresh competitor facts or current market research; browse or
  run a dedicated research workflow because ADR-282 cards intentionally flag
  named-competitor claims as freshness-sensitive.
- The question is about a consumer project's product positioning, not Cognitive
  OS itself.

## Fast path

1. From the SO repo root, answer through the cached primitive:

   ```bash
   scripts/cos-product-answer "<user question>" --format markdown
   ```

2. If the output includes:

   ```text
   Cache
   Using fresh product answer card
   Source freshness: fresh
   ```

   then use that answer. Do **not** read broad docs.

3. If the output falls back to live mode, refresh cards and retry:

   ```bash
   scripts/cos-product-answer-refresh --all
   scripts/cos-product-answer "<user question>" --format markdown
   ```

4. If a specific card is enough:

   ```bash
   scripts/cos-product-answer-refresh --question-id differentiator
   scripts/cos-product-answer --question-id differentiator --format markdown
   ```

## Available question IDs

The current question bank is in `manifests/product-question-bank.yaml`. Common
IDs:

- `differentiator`
- `non_differentiators`
- `existing_primitives`
- `automation_gap`
- `landing_pitch`
- `icp`
- `pricing`
- `competitors`

## Output discipline

When responding to the user:

- Prefer the `Short answer` and `Recommended pitch` sections.
- Include caveats from `Gaps` when the answer is `warn` or `partial`.
- Mention cache freshness when relevant.
- Do not upgrade `partial`, `partial-real`, or `warn` claims into universal
  claims.
- Do not publish private strategy wording verbatim; the card is a maintainer
  answer, not automatic public copy.

## Manual safety check for external copy

Before using wording externally, run:

```bash
scripts/cos-public-claim-gate --json
```

For named competitor comparisons, refresh external research first.

## Validation

```bash
python3 -m pytest tests/unit/test_product_answer.py tests/behavior/test_product_answer_cli.py -q
scripts/cos-product-answer-refresh --all --json
scripts/cos-product-answer "cuál es nuestro diferenciador" --json
```
