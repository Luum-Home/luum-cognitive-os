---
adr: 297
title: LLM-Dispatched Routing as Low-Confidence Fallback for the Skill Router
status: accepted
implementation_status: implemented
date: '2026-05-13'
supersedes: []
superseded_by: null
extends:
  - ADR-049
  - ADR-296
implementation_files:
  - lib/llm_routing_fallback.py
  - lib/skill_router.py
  - pytest.ini
  - tests/unit/test_llm_routing_fallback.py
tier: core
tags:
  - skill-router
  - llm-dispatch
  - fallback
  - vendor-neutral
verification_level: medium
classification_basis: |
  Adds a tertiary routing layer behind the existing regex (>=0.85) and
  semantic (>=0.55, ADR-296) gates. Triggers only when semantic returns
  >=3 candidates clustered in the 0.30-0.55 ambiguity band. Calls the
  LLM through lib/dispatch.dispatch (ADR-049, Qwen-primary,
  vendor-neutral) with a strict single-token prompt, caches decisions
  by sha256(prompt|sorted-candidate-names), and enforces a rolling
  hourly cap. Kill switch COS_DISABLE_LLM_ROUTING=1. Audit trail
  written to .cognitive-os/metrics/llm-routing.jsonl.
---

# ADR-297: LLM-Dispatched Routing as Low-Confidence Fallback

## Status

Accepted — 2026-05-13.

## Context

ADR-296 landed a multilingual semantic matcher (FastEmbed) that
resolves ~94% of routing decisions previously stranded below the 0.75
regex gate. The residual tail is structurally different from the
problem ADR-296 solved: the semantic layer *does* return candidates,
but they cluster together in the 0.30-0.55 band with no clear winner.
Operator screenshots show prompts where three to five skills sit
within 0.05 cosine of each other and the router silently returns
``None`` because nothing crosses the 0.55 confidence threshold.

A deterministic disambiguator (more regex, more intents, threshold
tuning) cannot close this gap — the prompts in question are genuinely
ambiguous to a token-based matcher and require lexical reasoning over
skill descriptions. The cheapest way to break the tie correctly is to
ask an LLM, but only when there is something to break.

## Decision

Add a third routing layer behind the existing regex (>=0.85) and
semantic (>=0.55) gates: an LLM-dispatched router that runs *only* on
ambiguous semantic ties.

**Trigger gate** — invoke the LLM iff:
1. ``0.30 <= semantic_top_confidence < 0.55``
2. At least 3 candidates fall inside ``[0.30, 0.55)``

Outside that band the existing layers already produce a decisive
answer (or correctly report no match) and the LLM adds latency and
cost without precision gain.

**Dispatch path** — all LLM calls flow through
:func:`lib.dispatch.dispatch` (ADR-049). The module MUST NOT import a
vendor SDK directly and MUST NOT hardcode a provider name. The
dispatch primary is Qwen, preserving Claude Max quota.

**Prompt** — minimal router-decision template:

```
You are routing a user prompt to one of the listed skills.
Reply with ONLY the skill name, nothing else.

User prompt:
{user_prompt}

Candidates (with descriptions):
- /skill-a: {description-a}
...

If none match, reply: NONE.
Reply with one of: /skill-a, /skill-b, ..., NONE.
```

**Strict parse** — accept exactly one token that matches one of the
listed invoke commands, or the literal ``NONE``. Anything else
(prose, hedging, multiple skills) → return ``None`` and DO NOT cache.

**Cache** — JSON files under ``.cognitive-os/cache/llm-routing/``,
keyed by ``sha256(prompt + "|" + sorted_candidate_names)[:16]``. TTL
defaults to 7 days, configurable via ``COS_LLM_ROUTING_CACHE_TTL_DAYS``.

**Rate limit** — rolling hourly counter stored at
``.cognitive-os/state/llm-routing-rate.json``. Default cap 100/h,
override via ``COS_LLM_ROUTING_HOURLY_CAP``. Cap exceeded → log
warning, return ``None`` (no dispatch).

**Kill switch** — ``COS_DISABLE_LLM_ROUTING=1`` short-circuits the
module before any work.

**Audit trail** — every invocation appends one JSONL line to
``.cognitive-os/metrics/llm-routing.jsonl`` recording event type,
prompt hash, chosen skill, confidence, latency, provider, and
cache-hit flag.

## Consequences

Positive:

* Closes the residual ambiguity tail that pure embeddings cannot
  resolve cleanly.
* Vendor-neutral via ADR-049 dispatch — provider swaps require no
  change to this module.
* Bounded cost: cache + hourly cap mean the worst-case spend is
  predictable and inspectable through ``llm-routing.jsonl``.
* Cheap when disabled: lazy dispatch import means the module loads in
  microseconds when ``COS_DISABLE_LLM_ROUTING=1``.

Negative:

* Adds end-to-end latency (up to ~2s p95) on the small fraction of
  prompts that hit the LLM path. Mitigated by cache + the narrow
  trigger gate (most prompts never reach this layer).
* Introduces an LLM-shaped dependency in the routing critical path,
  even though the fallback degrades to ``None`` on any failure. The
  regex and semantic layers continue to operate unchanged.
* Cache invalidation is time-based only — if a skill's description
  changes meaningfully, stale cached decisions persist until TTL
  expiry or manual purge.

## Verification

* Unit tests in ``tests/unit/test_llm_routing_fallback.py`` cover the
  kill switch, trigger gate (positive + negative), cache hit/miss,
  rate-limit degradation, strict parse, audit-trail write, and
  vendor-neutrality (grep-based source assertion).
* Live LLM tests are gated behind ``@pytest.mark.llm_routing`` and
  ``COS_LLM_ROUTING_LIVE_TEST=1`` so CI without provider credentials
  remains green.
* The semantic-matcher test suite (``test_semantic_skill_matcher.py``)
  continues to pass — no behaviour change above 0.55.

## Cross-references

* ADR-049 — LLM dispatch contract (Qwen primary, Claude fallback).
* ADR-296 — Language-agnostic semantic routing (the layer this
  module sits behind).
* ADR-285 — Skill registry runtime drift detection (descriptions
  consumed by this layer come from the same metadata source).
