---
adr: 296
title: Language-Agnostic Semantic Routing for the COS Skill Router
status: accepted
implementation_status: implemented
date: '2026-05-13'
supersedes: []
superseded_by: null
extends:
  - ADR-039
  - ADR-174
  - ADR-285
implementation_files:
  - lib/semantic_skill_matcher.py
  - pyproject.toml
  - manifests/dependency-adoption-evidence.yaml
  - skills/product-answer/SKILL.md
  - tests/unit/test_semantic_skill_matcher.py
tier: core
tags:
  - skill-router
  - semantic
  - multilingual
  - fastembed
verification_level: medium
classification_basis: |
  Replaces lib/semantic_skill_matcher.py (Jaccard) with a multilingual
  embedding matcher (FastEmbed) wired behind the existing 0.75-regex gate
  in lib/skill_router.py. Pyproject extra + adoption evidence + tests
  landed atomically; the Spanish capability-question acceptance test
  resolves to /product-answer at confidence > 0.6.
---

# ADR-296: Language-Agnostic Semantic Routing for the COS Skill Router

## Status

Accepted — 2026-05-13.

## Context

The skill router in `lib/skill_router.py` is regex-first by design (cheap,
deterministic). When the top regex match falls below 0.75 confidence the
router consults a *semantic fallback* in `lib/semantic_skill_matcher.py`.
That fallback was diagnosed as broken in three concrete ways:

1. **Optional embedding dep not installed.** The module attempted to import
   `sentence-transformers`. In production that package is not in the install
   manifest, so every call silently fell back to the Jaccard branch.
2. **Jaccard collapses across languages.** Token overlap between a Spanish
   user prompt and the English `description` corpus is effectively zero
   even with diacritic stripping. The fallback returned 0.0 for every
   non-English prompt.
3. **Only 19 / 196 skills declared `routing_intents`.** Even if the matcher
   worked, only ~10 % of the catalog was visible to it, because the prior
   implementation refused to register skills without explicit intents.

A real failing case (operator screenshot, used as the acceptance test):

```
"Si yo soy un dev que tengo limitaciones en cuanto al conocimiento de las
 buenas prácticas, codigo y arquitectura limpia, seguridad, construcción
 de tests, documentación, primitivas de agentes, entre otras cosas, este
 SO me puede ayudar?"
```

Expected: `/product-answer` at confidence > 0.6. Pre-ADR result: NONE.

## Decision

Replace the Jaccard matcher with a multilingual embedding matcher backed
by **FastEmbed** (qdrant, MIT). The chosen model is
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (Apache-2.0,
~220 MB ONNX, 50+ languages, ~9 ms warm latency on CPU). All 196 skills
participate — the corpus per skill is `routing_intents (if any) +
description + summary_line`. Cosine similarity is the score; the
calibrated cutoff is **0.50** (env-overridable via
`COS_SEMANTIC_THRESHOLD`). Scores above the gate are linearly mapped onto
the `[0.55, 0.85]` confidence band so the regex layer (which fires at
≥ 0.75 with priority) always wins when both layers match.

### Threshold calibration

The 0.50 default was chosen so that:

- the held-out multilingual prompt set in
  `tests/unit/test_semantic_skill_matcher.py` reaches precision ≥ 0.8
  across EN / ES / PT / DE / FR / IT;
- the operator's verbose Spanish capability question (above) resolves to
  `/product-answer` at confidence ≥ 0.6;
- diffuse prompts that match no skill above 0.50 return an empty list (so
  the orchestrator does not auto-invoke a marginal skill).

The cutoff is intentionally conservative — short utterances on the
multilingual MiniLM family often peak at 0.6–0.7, so 0.50 catches them
without admitting unrelated noise.

### Why FastEmbed, not `aurelio-labs/semantic-router`

The survey recommended consuming the upstream router library. At adoption
time the live PyPI release is stuck at `semantic-router==0.0.3`: it ships
no `Route` / `RouteLayer` symbols and is not importable on Python 3.14.
The `0.1.x` line referenced in the upstream README has not been published.
We therefore consume FastEmbed directly. The routing arithmetic (cosine
top-k, threshold gate, confidence calibration) is ~30 lines and there is
no value in adding a thin third-party wrapper around it.

## Operational Guide

### Adding / removing skills

Drop a `SKILL.md` with frontmatter `description`, `summary_line`, and
(optionally) `routing_intents`. The matcher rebuilds its catalog on the
next process boot. The on-disk cache under
`.cognitive-os/cache/semantic-router/catalog-<sha>.json` is keyed by a
SHA over `(model name, every skill name, every corpus line)` — any drift
invalidates the cache and the next call re-indexes.

### Inspecting routes

```python
from lib.skill_router import SkillRouter
r = SkillRouter()
print([(m.skill_name, m.confidence, m.reason) for m in r.match("...")])
```

The semantic layer fires only when the top regex confidence is below
0.75; semantic matches carry `reason="Semantic match (cos=…, model=…)"`.

### Kill switch

Set `COS_DISABLE_SEMANTIC_ROUTING=1` in the environment. The matcher
returns `[]` immediately, before any model load — the regex layer keeps
working unchanged.

### Tuning

| Env var | Effect | Default |
|---------|--------|---------|
| `COS_DISABLE_SEMANTIC_ROUTING` | Disable semantic fallback entirely | unset |
| `COS_SEMANTIC_THRESHOLD` | Override cosine cutoff (e.g. `0.45` for more recall, `0.60` for fewer false positives) | `0.50` |

### `routing_intents` field — what it's for

Optional. A list of reference utterances or structured-intent dicts. The
loader accepts both:

```yaml
routing_intents:
  - intent: capability_question
    description: User asks what the OS can do for them.
  - "can this help me as a developer?"
  - "¿puede ayudarme como desarrollador?"
```

Use it when a skill's `description` is too abstract to differentiate from
near-neighbours under embedding similarity. `product-answer` is the
canonical example.

## Alternatives Considered

- **SLM-as-router (Qwen 2.5 0.5B / Phi-3 mini).** Higher quality on long
  queries but ~150–300 ms latency per request, plus a 1 GB+ model on
  disk. Overkill for routing.
- **mDeBERTa-v3 zero-shot NLI.** O(N) candidate scans per request — does
  not scale past ~50 labels without a re-ranker stage.
- **jinaai/jina-embeddings-v3.** Strong multilingual numbers but the
  license is non-commercial.
- **txtai.** Adds an indexer + heavier deps; the hybrid sparse/dense
  value-add is marginal for ≤ 200 short corpus entries.

## Consequences

- The decision is now part of the governed Cognitive OS primitive surface and must stay aligned with implementation, tests, and runtime projection metadata.

## Alternatives rejected

- **Leave the behavior as implicit agent instruction only.** Rejected because this ADR records a runtime/authoring contract that needs durable tests or audits rather than conversation-only memory.

## Verification

```bash
# Acceptance: Spanish capability question routes to /product-answer
python3 -c "from lib.semantic_skill_matcher import SemanticSkillMatcher; \
            from lib.skill_router import SkillRouter; \
            r=SkillRouter(); m=r.match('Si yo soy un dev que tengo limitaciones...'); \
            print(m[0])"

# Test suite (requires fastembed installed)
python3 -m pytest tests/unit/test_semantic_skill_matcher.py -v

# ADR implementation audit (must report 0 overclaims)
python3 scripts/cos-adr-implementation-audit.py --strict
```

## Migration

- `lib/semantic_skill_matcher.py` has been **rewritten** (reconstruction
  phase, no compat shim). Public surface preserved:
  `SemanticSkillMatcher`, `SemanticMatch`, `load_skill_metadata`,
  `SemanticSkillMatcher.from_routing_table()`,
  `SemanticSkillMatcher.match()`. The `llm_classify` helper has been
  removed — it was unused by `skill_router.py` and orchestrators never
  opted in.
- `SKILL.md` `description` is now the **source of truth** for skill
  routing. `routing_intents` remains supported as an optional list of
  additional utterances (string form) or structured intents (dict form).
- The legacy `intent_examples` field is still ignored by the loader.
  SKILL.md authors should consolidate examples under `routing_intents`
  as plain strings.

## Risks

| Risk | Mitigation |
|------|------------|
| Cold-start cost on first call (200–500 ms model load + 1.5 s catalog embed for 196 skills) | Embeddings are cached to disk and re-used for the lifetime of the catalog SHA. |
| Operators forget `fastembed` is opt-in | Matcher logs a one-line warning and degrades to `[]`; the regex layer keeps working. |
| Future PyPI publication of `aurelio-labs/semantic-router 0.1.x` | We can adopt it later — the public surface of this module would not change. |

## Evidence

Tier claim evidence is maintained through the boring-reliability control-plane lane:

```bash
scripts/cos-boring-reliability --json
scripts/cos-tier-claim-audit --json
```

This ADR remains `tier: core` because it affects default routing, observability,
or primitive-governance behavior that is part of the core operator control
plane. The tier claim is re-audited by `scripts/cos-tier-claim-audit`.
