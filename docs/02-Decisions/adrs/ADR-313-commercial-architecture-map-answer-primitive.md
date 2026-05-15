---
adr: 313
title: Commercial Architecture Map Answer Primitive
status: accepted
implementation_status: implemented
date: '2026-05-14'
supersedes: []
superseded_by: null
implementation_files:
  - manifests/product-question-bank.yaml
  - manifests/product-claim-evidence.yaml
  - skills/architecture-map-answer/SKILL.md
  - tests/behavior/test_product_answer_cli.py
tier: maintainer
tags:
  - product
  - architecture
  - evidence
  - commercial-positioning
  - claim-safety
classification_basis: accepted and implemented as a curated product-answer question plus claim-evidence row and dedicated maintainer skill; the output is generated through ADR-280/282 product-answer infrastructure rather than ad-hoc chat.
verification:
  level: medium
  commands:
    - python3 -m pytest tests/behavior/test_product_answer_cli.py -q
    - scripts/cos-product-answer --question-id architecture_map --format markdown --no-cache
  proves:
    - architecture_map question routes through the evidence-backed product-answer primitive
    - public/commercial wording avoids internal tool names and implementation inventory
    - Mermaid output is provided in a compatible graph form
    - unsafe claims and growth/adaptation gaps remain visible
---

# ADR-313 — Commercial Architecture Map Answer Primitive

## Status

Accepted and implemented — 2026-05-14.

<!-- SCOPE: OS -->

## Context

Cognitive OS already has enough evidence to answer product and commercial
questions through ADR-280 and ADR-282. It also has a rich architecture: agentic
primitives, lifecycle governance, memory, evidence ledgers, projection profiles,
and service surfaces. The problem is that architecture explanations can easily
leak implementation vocabulary or become stale as the SO grows.

The recurring operator need is different from a technical inventory. The desired
answer is a compact, commercial-safe architecture map that explains the value of
the SO without exposing internal tool names, counts, or half-mature runtime
surfaces as public promises.

The first manual version of the answer worked because it mapped internal
architecture to stable commercial categories:

- guardrails;
- policies;
- playbooks;
- persistent memory;
- auditable evidence;
- adapters over existing development tools;
- future service surfaces.

That answer should not remain chat-only. If Cognitive OS sells evidence-backed
trust, its own architecture narrative must be generated from governed evidence.

## Decision

Add a curated **Commercial Architecture Map Answer Primitive** as an extension of
the ADR-280/282 product-answer system.

The primitive is exposed as the `architecture_map` question id in
`manifests/product-question-bank.yaml` and grounded by a dedicated claim row in
`manifests/product-claim-evidence.yaml`.

The primitive must produce:

1. a compact commercial-safe architecture explanation;
2. a Mermaid-compatible graph that avoids fragile formatting;
3. safe pitch language;
4. unsafe claims to avoid;
5. growth/adaptation caveats;
6. a trust report inherited from the product-answer runtime.

The primitive must not:

- lead with implementation counts or internal tool names;
- name specific harnesses/providers in public-mode wording;
- imply universal cross-tool parity;
- imply autonomous self-improvement or fully hosted service readiness;
- turn private strategy or in-progress runtime surfaces into publication-ready
  copy.

## Public narrative contract

The stable public map is not the implementation inventory. It is the value chain:

```text
Engineering team
  -> coding agents
  -> Cognitive OS governance and evidence layer
  -> guardrails, policies, playbooks, memory, evidence
  -> operational trust
  -> safer, more verifiable, more scalable agent work
```

Internal primitives may change, split, or grow. The public categories should stay
stable unless product positioning changes.

## Adaptation model

As the SO grows, update the mapping and maturity rows, not the public narrative
from scratch:

```text
commercial category
  -> approved source docs
  -> related claim ids
  -> maturity/status boundary
  -> safe public wording
  -> unsafe claims to avoid
```

This lets new primitives improve the evidence behind a category without making
the pitch depend on volatile implementation details.

## Implementation

Implemented by:

- adding `architecture_map` to `manifests/product-question-bank.yaml`;
- adding `commercial_architecture_map_primitive` to
  `manifests/product-claim-evidence.yaml`;
- adding `skills/architecture-map-answer/SKILL.md` as the maintainer workflow;
- extending product-answer behavior tests so the CLI routes architecture-map
  questions and keeps public wording sanitized.

The implementation intentionally reuses `scripts/cos-product-answer` instead of
creating a parallel generator. This keeps freshness checks, trust reports,
claim-safety boundaries, cache cards, and strict-mode behavior in one place.

## Consequences

### Positive

- The architecture map becomes reproducible and evidence-backed.
- Commercial explanations can stay aligned with claim safety as the SO evolves.
- The answer can be refreshed through existing product-answer card machinery.
- Maintainers get a clear place to update public-safe architecture wording.

### Negative / trade-offs

- The first version is curated, not fully derived from every primitive contract.
- The map intentionally hides internal implementation detail in public/commercial
  mode, so deeper due-diligence still needs technical docs.
- If product positioning changes, the question bank and claim evidence need an
  explicit update.

## Alternatives rejected

- Leave the decision implicit in conversation history: rejected because ADR-gated governance needs a durable, reviewable record with explicit trade-offs.
- Treat this as an unversioned implementation note: rejected because the behavior affects operator-facing contracts and must survive refactors.

## Verification

```bash
python3 -m pytest tests/behavior/test_product_answer_cli.py -q
scripts/cos-product-answer --question-id architecture_map --format markdown --no-cache
```
