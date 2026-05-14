---
adr: 294
title: 'Memory Quality Scoring: Four-Dimension Quality Fields and min_quality Filter for Engram v3'
status: accepted
implementation_status: implemented
date: '2026-05-13'
supersedes: [ADR-290]
extends: [ADR-287]
superseded_by: null
implementation_files:
  - lib/engram_wave3_schema.py
  - lib/engram_fts5_search.py
tier: maintainer
tags:
  - memory
  - engram
  - retrieval
  - schema
classification_basis: additive schema extension of ADR-287 Claim dataclass with four nullable float fields and a new search filter; the original ADR-290 bundle hid this amendment to ADR-287 inside a five-pattern omnibus and that silence is the bug this ADR repairs
verification:
  level: strong
  commands:
    - python3 -m pytest tests/unit/test_engram_quality_scoring.py -q
  proves:
    - quality_score_weights_and_filter_deterministic
    - search_bm25_min_quality_none_is_backwards_compatible
    - search_bm25_min_quality_positive_excludes_missing_fields
---

# ADR-294 — Memory Quality Scoring (Extends ADR-287)

## Status

Accepted

**Date:** 2026-05-13
**Owner:** orchestrator
**Tier:** maintainer
**Authors:** orchestrator
**Supersedes:** ADR-290 (Pattern 4 split out of the original five-pattern bundle)
**Extends:** ADR-287 (Engram v3 evidence-grounded claims)
**Related:** ADR-292, ADR-293, ADR-295 (peer splits of ADR-290)

---

## Context

ADR-287 added evidence linkage to engram v3 claims, but every claim is still treated as equally retrievable. There is no way for a writer to attach a structured quality estimate (completeness, relevance, clarity, accuracy) and no way for a reader to filter low-quality claims out of a search.

This is a **schema amendment to ADR-287**, not a standalone primitive. In ADR-290 the amendment was bundled with four unrelated patterns and was not visible as an ADR-287 change in the ADR index or in `extends:` linkage. That silence is the central reason this ADR exists as a standalone split: a downstream reader of ADR-287 had no way to discover the `min_quality` semantics by reading ADR-287 alone. This ADR repairs that with an explicit `extends: [ADR-287]` backref.

---

## Decision

Additively extend the v3 `Claim` dataclass in `lib/engram_wave3_schema.py` with four optional `float | None` fields scored on `[0, 1]`:

- `quality_completeness`
- `quality_relevance`
- `quality_clarity`
- `quality_accuracy`

Add a pure function `compute_quality_score(completeness, relevance, clarity, accuracy, weights=None) -> float` that returns the weighted mean (uniform 0.25 default weights, inputs clamped to `[0, 1]`).

Add a `min_quality: float | None = None` parameter to `search_bm25` in `lib/engram_fts5_search.py`.

### Filtering policy (silent semantic change — called out explicitly)

The original ADR-290 buried two policy choices that have real semantic weight. They are surfaced here in plain text:

1. **`min_quality is None` (default) → filter disabled.** Every existing claim continues to surface. This is the backwards-compatible path and the regression-guard test pins it.
2. **`min_quality > 0` → claims with any missing quality field are treated as quality 0 and filtered out.** This is the "missing == 0" policy. A writer who supplies three of four quality fields and forgets the fourth will be filtered out at any `min_quality > 0`. This is conservative on purpose: the alternative (impute mean, or skip the field in the average) would let half-scored claims out-rank fully-scored claims under common weights, which is the opposite of what a reader asking for `min_quality > 0` wants.

**Silent-change disclosure.** Before this ADR, `search_bm25` had no `min_quality` parameter; any caller that adopts `min_quality > 0` will observe a strictly smaller result set than `min_quality=None` on the same database, even if no claims have been scored. That is the intended semantics, but it is a behavior change at the call-site level and must be documented in `search_bm25`'s docstring (covered by the implementation test).

### Test approach

- `compute_quality_score` is deterministic with custom weights and clamps inputs to `[0, 1]`.
- `search_bm25` with `min_quality=None` returns the same result set as before — regression guard for backwards compatibility.
- `search_bm25` with `min_quality > 0` excludes rows where any of the four quality columns is `NULL`.
- Rows with all four columns scored above the threshold pass.

---

## Operational Guide

- **Writers.** Optional. Existing engram write paths continue to work unchanged — the schema columns are nullable. Writers that have quality signals supply them via the existing write path.
- **Readers.** Optional. Existing `search_bm25` callers omit `min_quality` and observe identical behavior. Readers that want quality filtering pass `min_quality=0.7` (or similar) and accept the "missing == 0" policy.
- **Migration.** Additive; no migration required for ADR-287 callers.

---

## Consequences

### Positive

- Strict extension of ADR-287; existing callers continue to work because every new field defaults to `None` and `min_quality` defaults to `None` (disabled).
- Reader-driven filter — zero write-side cost when scores are not supplied.
- The amendment to ADR-287 is now visible in the ADR index, in `extends: [ADR-287]`, and in `lib/engram_fts5_search.py`'s docstring. ADR-290's silence on this amendment is repaired.

### Negative

- The "missing == 0" policy is conservative. A writer who supplies three of four quality fields and forgets the fourth will be filtered out at any `min_quality > 0`. Documented in the function docstring and reproduced in this ADR.

### Risks

- A future reader who interprets `min_quality > 0` as "average of available fields" will be surprised by the empty result set. Mitigated by the function docstring and by the explicit test that exercises the missing-field case.

---

## Alternatives Rejected

The ADR-290 bundle omitted these alternatives. They are recorded here because each one was considered and rejected, and a future reader of the schema deserves to see the reasoning.

1. **Single binary `is_high_quality: bool` flag instead of four floats.** Rejected because a binary flag collapses four orthogonal signals (completeness, relevance, clarity, accuracy) into one bit. Readers cannot rebalance weights, and writers cannot express partial quality. The four-float shape composes; a binary flag does not.
2. **`min_quality is None` vs `min_quality > 0` as the "disabled" sentinel.** `None` chosen because `0.0` is a valid threshold ("keep everything that has a score, even if low") and conflating it with "disabled" would make that threshold unexpressible. The cost is a slightly heavier signature; the benefit is that all of `[0.0, 1.0]` remains semantically meaningful as a threshold.
3. **Missing-field policy: "missing == 0" vs "missing == mean of supplied fields" vs "skip in average".** "Missing == 0" chosen because it is the only policy that makes `min_quality > 0` unambiguously mean "I have actively scored this claim and it cleared the bar". The "mean of supplied" alternative would silently boost claims with only one or two high scores; the "skip in average" alternative would let a one-scored claim with `quality_accuracy=1.0` outrank a fully-scored claim averaging `0.95`. Both alternatives invert the reader's intent.

---

## Alternatives rejected

- **Leave the behavior as implicit agent instruction only.** Rejected because this ADR records a runtime/authoring contract that needs durable tests or audits rather than conversation-only memory.

## Verification

```bash
python3 -m pytest tests/unit/test_engram_quality_scoring.py -q
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

These checks prove that the quality score function is deterministic and clamps inputs, that `min_quality=None` preserves ADR-287 behavior, that `min_quality > 0` filters claims missing any quality field, and that the ADR satisfies the post-ADR-067 documentation contract.
