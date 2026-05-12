---
adr: 280
title: Product Question-to-Evidence Primitive
status: accepted
implementation_status: implemented
classification_basis: 'implemented: ADR-280 ships manifests/product-question-bank.yaml, manifests/product-claim-evidence.yaml, lib/product_answer.py, scripts/cos-product-answer, docs/business/product-answer-playbook.md, and unit/behavior tests for evidence-backed product answers.'
date: 2026-05-12
supersedes: []
superseded_by: null
extends: [ADR-120, ADR-201, ADR-206, ADR-252, ADR-256, ADR-277]
implementation_files:
  - manifests/product-question-bank.yaml
  - manifests/product-claim-evidence.yaml
  - lib/product_answer.py
  - scripts/cos-product-answer
  - docs/business/product-answer-playbook.md
  - tests/unit/test_product_answer.py
  - tests/behavior/test_product_answer_cli.py
tier: maintainer
tags: [product, evidence, commercial-questions, claim-safety, messaging, automation]
---
# ADR-280: Product Question-to-Evidence Primitive

## Status

Accepted and implemented — 2026-05-12.

<!-- SCOPE: OS -->

**Date**: 2026-05-12

## Context

Cognitive OS has enough product and architecture evidence to answer recurring
commercial and product questions, but the answer surface was conversation-led.
The differentiator can be stated from existing docs:

> Cognitive OS is the operational layer that makes coding agents verifiable,
> governable, coordinated, and portable across tools, with executable evidence
> for what they did.

The stronger commercial wedge is behavioral governance plus an evidence layer
for agentic development: agents must prove claims, respect coordination and
blast-radius controls, expose cost-to-outcome, and leave replayable receipts.

The risk is that future agents answer product questions from memory, confidence,
or stale strategy prose. That creates the same failure mode the product itself
claims to prevent: unverified claims. Product messaging must therefore be
answerable from versioned evidence, not improvised from chat.

Existing primitives solve adjacent slices:

- ADR-120 classifies whether a conversation should become a primitive.
- ADR-201 converts telemetry into governed improvement proposals.
- ADR-206 blocks unsafe public claims without evidence.
- ADR-252 maps feature claims to reality levels.
- ADR-256 joins primitive contracts to runtime evidence.
- ADR-277 prevents documentation truth drift for volatile claims.

No primitive composes those ideas into a fast product/commercial question answer.

## Decision

Add a deterministic **Product Question-to-Evidence Primitive** exposed as:

```bash
scripts/cos-product-answer "¿Cuál es nuestro diferenciador?" --json
scripts/cos-product-answer --question-id differentiator --format markdown
```

The primitive must:

1. classify a product or commercial question against a versioned question bank;
2. load only approved source paths for that question;
3. join source paths to explicit product claim evidence;
4. detect unsafe or aspirational claims before producing an answer;
5. emit a short answer, longer answer, recommended pitch, evidence paths,
   unsafe claims to avoid, known gaps, confidence, and a trust report;
6. fail in strict mode when evidence files are missing or selected claims are
   blocked;
7. remain read-only and suitable for manual use, tests, release review, and
   future maintainer-agent automation.

The first implementation covers these recurring questions:

- what differentiates Cognitive OS;
- what Cognitive OS should not claim as its differentiator;
- which existing primitives answer product questions today;
- which automation is missing for product/commercial questions;
- what the landing pitch should say.

## Product answer contract

The answer source of truth is split in two manifests:

| Manifest | Responsibility |
|---|---|
| `manifests/product-question-bank.yaml` | question IDs, aliases, keywords, approved sources, answer text, pitch, unsafe claims, gaps, and related claim IDs |
| `manifests/product-claim-evidence.yaml` | claim IDs, reality status, evidence paths, maturity, confidence, and public wording boundaries |

Generated answers use the lowest selected claim maturity as the aggregate
`claim_status`. The status ordering is:

```text
real > partial-real > partial > aspirational > blocked
```

Blocked claims are never allowed in a passing strict answer. Aspirational claims
may appear only as explicit gaps or non-claims.

## Non-goals

- Do not replace competitive fact-checking. External market claims still require
  fresh research before publication.
- Do not turn private strategy docs into public copy automatically.
- Do not auto-edit landing pages, README, or sales decks.
- Do not bypass ADR-206 public claim gate.
- Do not claim universal cross-IDE parity or autonomous self-improvement unless
  separate evidence upgrades those claims.

## Consequences

### Positive

- Product and commercial questions become reproducible instead of ad hoc.
- Agents can answer the differentiator question quickly without rereading the
  whole repo.
- Claim safety becomes part of messaging generation, not a later review step.
- The primitive creates a bridge from strategy docs to evidence-backed public
  wording.
- Future maintainer loops can update question answers when evidence changes.

### Negative / trade-offs

- The first question bank is intentionally small and curated.
- Strong competitive positioning remains conservative until external landscape
  research is refreshed.
- The primitive may reject punchier wording when supporting evidence is partial.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Continue answering from chat memory | Recreates unverified-claim risk and does not scale as docs grow. |
| Put all product answers in one Markdown FAQ | Human-readable but not machine-checkable, strict, or evidence-joined. |
| Use ADR-206 only | ADR-206 blocks high-risk public claims but does not classify questions or generate answers. |
| Fully autonomous marketing generator | Too risky for a trust product; publication still needs human review and fresh competitive fact-checking. |

## Verification

```bash
python3 -m pytest tests/unit/test_product_answer.py tests/behavior/test_product_answer_cli.py -q
scripts/cos-product-answer "¿Cuál es nuestro diferenciador?" --json
scripts/cos-product-answer --question-id differentiator --format markdown
```
