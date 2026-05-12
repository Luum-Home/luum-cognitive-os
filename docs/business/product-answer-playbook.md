# Product Answer Playbook

## Purpose

Product and commercial answers for Cognitive OS must follow the same trust
standard as runtime agent work: claims need evidence, maturity, known gaps, and
unsafe wording boundaries.

Use the ADR-280 primitive whenever a question asks about positioning, ICP,
commercial pitch, product wedge, claims, or what COS can safely promise.

## Canonical command

```bash
scripts/cos-product-answer "¿Cuál es nuestro diferenciador?" --json
scripts/cos-product-answer --question-id differentiator --format markdown
```

## Product north star

Cognitive OS is the behavioral governance and evidence layer for agentic
development. It makes fast but opaque coding agents prove work, coordinate
safely, expose cost/risk, and leave replayable receipts across supported tools.

Short pitch:

> AI agents ship faster. Cognitive OS makes them prove it.

Spanish variant:

> Tus agentes programan más rápido. Cognitive OS los obliga a probarlo.

## Answer discipline

1. Start from `manifests/product-question-bank.yaml`.
2. Join every answer to `manifests/product-claim-evidence.yaml`.
3. Treat `blocked` claims as non-publishable.
4. Treat `aspirational` claims as roadmap/gaps, not shipped behavior.
5. Mention uncertainty when competitive or market claims may have changed.
6. Use private strategy docs as evidence context, not as public copy.

## Manual check

Before using an answer externally, run:

```bash
scripts/cos-product-answer --question-id differentiator --json
scripts/cos-public-claim-gate --json
```

For named competitor comparisons, refresh external research before publishing.

## Maintainer update flow

When product evidence changes:

1. update or add claim rows in `manifests/product-claim-evidence.yaml`;
2. update question rows in `manifests/product-question-bank.yaml`;
3. add or update tests in `tests/unit/test_product_answer.py` and
   `tests/behavior/test_product_answer_cli.py`;
4. rerun the ADR-280 verification commands;
5. update public docs only after the generated answer and public claim gate pass.
