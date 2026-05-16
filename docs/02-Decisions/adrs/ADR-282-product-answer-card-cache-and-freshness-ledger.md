---
adr: 282
title: Product Answer Card Cache and Freshness Ledger
status: accepted
implementation_status: implemented
classification_basis: 'implemented: ADR-282 ships answer-card materialization, source-hash freshness checks, compact routing index, refresh CLI, cached cos-product-answer read path, docs, and unit/behavior tests.'
date: 2026-05-12
supersedes: []
superseded_by: null
extends: [ADR-120, ADR-206, ADR-252, ADR-277, ADR-280]
implementation_files:
  - lib/product_answer.py
  - scripts/cos-product-answer
  - scripts/cos-product-answer-refresh
  - docs/08-References/business/product-answer-playbook.md
  - tests/unit/test_product_answer.py
  - tests/behavior/test_product_answer_cli.py
tier: maintainer
tags: [product, evidence, cache, freshness, token-efficiency, commercial-questions]
---
# ADR-282: Product Answer Card Cache and Freshness Ledger

## Status

Accepted and implemented — 2026-05-12.

<!-- SCOPE: OS -->

**Date**: 2026-05-12

## Context

ADR-280 made product and commercial answers evidence-backed, but not maximally
token-efficient. Without a materialized cache, an agent still has to load the
question bank, claim evidence, source lists, and generated answer structure for
frequent questions. That is far cheaper than rereading the whole SO, but it does
not fully solve the operator problem:

```text
product/commercial question
→ explore docs / ADRs / manifests / primitives
→ synthesize a short answer
→ repeat for the next similar question
```

As Cognitive OS grows, repeated product questions must be answerable from a
compact precomputed surface. The agent should not inspect dozens of documents to
answer “what is the differentiator?” when the vetted answer and its evidence
fingerprints already exist.

## Decision

Add an ADR-282 answer-card materialization layer over ADR-280:

```bash
scripts/cos-product-answer-refresh --all
scripts/cos-product-answer-refresh --question-id differentiator
scripts/cos-product-answer "What is our differentiator?"
```

The refresh primitive generates ignored local artifacts under:

```text
.cognitive-os/product-answers/{question_id}.md
.cognitive-os/product-answers/{question_id}.json
.cognitive-os/product-answers/index.yaml
.cognitive-os/product-answers/freshness-ledger.jsonl
```

`cos-product-answer` now checks for a fresh answer card first. If the card exists
and every recorded source hash still matches, it uses the card. If the card is
missing or stale, it falls back to the ADR-280 live manifest path.

## Card contract

Each Markdown answer card has YAML frontmatter with:

```yaml
schema_version: product-answer-card/v1
adr: ADR-282
question_id: differentiator
last_generated: '2026-05-12T00:00:00Z'
status: fresh
answer_status: warn
claim_status: partial
confidence: 0.78
trust_score: 78
source_hashes:
  manifests/product-question-bank.yaml: sha256...
  manifests/product-claim-evidence.yaml: sha256...
  docs/08-References/business/product-messaging.md: sha256...
```

The body is the compact ADR-280 Markdown answer.

The JSON sidecar preserves the full machine-readable answer report plus cache
metadata so tools do not need to parse Markdown.

## Freshness model

A card is `fresh` only when:

1. the Markdown card exists;
2. the JSON sidecar exists;
3. every source path recorded in `source_hashes` exists;
4. every current SHA-256 equals the stored SHA-256.

Any source hash drift marks the card `stale`. Stale cards are not used by
`cos-product-answer`; they are regenerated explicitly through
`cos-product-answer-refresh`.

## Compact routing index

`index.yaml` provides a small routing surface:

```yaml
schema_version: product-answer-routing-index/v1
entries:
  differentiator:
    card: .cognitive-os/product-answers/differentiator.md
    aliases: [diferenciador, factor diferenciador, what is our differentiator]
    keywords: [diferenciador, differentiator, wedge]
    max_answer_tokens: 700
    freshness: fresh
```

Agents can inspect this compact index before deciding whether any larger source
read is necessary.

## Non-goals

- Do not commit generated `.cognitive-os/product-answers/*` cards; they are
  local derived artifacts.
- Do not remove ADR-280 live generation; it remains the fallback and refresh
  source.
- Do not make stale cards authoritative.
- Do not make product answers publication-approved without the public claim gate
  and human review.

## Consequences

### Positive

- Frequent product/commercial questions become cheap to answer.
- Agents can use a small routing index and one answer card instead of broad repo
  investigation.
- Freshness is explicit and machine-checkable through source hashes.
- Generated answers stay tied to ADR-280 evidence and trust reports.

### Negative / trade-offs

- A refresh step is required after source changes.
- Derived cards are local state and may differ between worktrees until refreshed.
- The first implementation uses file hashes, not semantic diffs; any source edit
  invalidates the card even if the answer would not change.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep only ADR-280 live generation | Correct but still repeats manifest/source processing for frequent questions. |
| Commit generated answer cards | Creates derived-artifact drift and merge noise; local caches are enough. |
| Trust stale cards with a warning | Reintroduces stale product-claim risk. |
| Use embeddings/vector search over all docs | More moving parts and token cost than a deterministic curated cache for frequent questions. |

## Verification

```bash
python3 -m pytest tests/unit/test_product_answer.py tests/behavior/test_product_answer_cli.py -q
scripts/cos-product-answer-refresh --question-id differentiator --json
scripts/cos-product-answer "What is our differentiator?" --json
```
