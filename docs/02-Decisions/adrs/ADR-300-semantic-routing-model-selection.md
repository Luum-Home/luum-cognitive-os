---
adr: 300
title: Semantic Routing Model Selection — Operator Swap + Benchmark Winner Discovery
status: accepted
implementation_status: implemented
date: '2026-05-13'
supersedes: []
superseded_by: null
extends:
- ADR-296
- ADR-297
- ADR-298
implementation_files:
- lib/semantic_skill_matcher.py
- manifests/routing-benchmark-models.yaml
- docs/06-Daily/reports/routing-benchmark-2026-05-13.md
tier: core
tags:
- skill-router
- benchmark
- model-selection
- operator-config
verification_level: medium
classification_basis: semantic routing model selection implemented with deterministic
  manifest, runtime loader, CLI, and tests; no remaining in-scope work for this ADR,
  and future model/provider expansion is separate/out-of-scope follow-up
---

# ADR-300: Semantic Routing Model Selection — Phase 1

## Status

Accepted — 2026-05-13.

## Context

ADR-296 chose `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` as the
semantic matcher backbone. ADR-298 built a benchmark harness as the canonical
empirical-evidence tool for model-selection decisions. This ADR closes the loop:
runs the benchmark, documents the winner, and exposes the swap mechanism.

The headline result of `docs/06-Daily/reports/routing-benchmark-2026-05-13.md`:

| model | precision@1 | warm-p95 | peak MB | License |
|---|---:|---:|---:|---|
| `intfloat/multilingual-e5-large` | **0.897** | 47.0 ms | 1654 | MIT |
| `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | 0.810 | **15.4 ms** | 1654 | Apache |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (current default) | 0.753 | 26.6 ms | 840 | Apache |

Per-language: `multilingual-e5-large` is **+14 pts** precision@1 on average over
the current default — with the largest gains on the previously weak languages:
PT (+18) and FR (+16).

The harness also attempted `BAAI/bge-m3`, `Qwen/Qwen3-Embedding-0.6B`, and
`microsoft/harrier-oss-v1-270m`. All three failed to load because they are not
registered in FastEmbed's curated `TextEmbedding` list. They remain in the
manifest as aspirational entries for a future ONNX-direct adapter (out of scope
for this ADR).

## Decision

### Phase 1 (this ADR)

1. **Document the benchmark winner.** `multilingual-e5-large` is the
   empirically-strongest license-clean candidate at p95<500ms and precision@1.
2. **Expose a runtime swap.** New env var `COS_SEMANTIC_ROUTING_MODEL` overrides
   `DEFAULT_MODEL_NAME` at import time. Operators can experiment with the
   benchmark winner without committing the default change:
   ```
   COS_SEMANTIC_ROUTING_MODEL=intfloat/multilingual-e5-large
   ```
3. **Keep the current default** (`paraphrase-multilingual-MiniLM-L12-v2`)
   unchanged. See §Rationale below for why.

### Phase 2 — REJECTED 2026-05-13 after empirical exploration

**Attempted**: adopt `multilingual-e5-large` as the default with a recalibrated
`DEFAULT_THRESHOLD`.

**Finding**: no single threshold value satisfies the current test contract.
Measured cosine distribution under e5-large on the same prompt corpus:

| Prompt class | Cosine | Mapped confidence |
|---|---:|---:|
| Greetings ("hello", "thanks") | 0.80 | 0.68 |
| Negative-context (skill mentions in critique) | 0.84 – 0.86 | 0.73 – 0.76 |
| Screenshot-bug Spanish prompt (TRUE positive) | 0.906 | 0.77 |
| Clean positive prompts | 0.95 – 0.99 | 0.94 – 0.96 |

The screenshot-bug prompt (a legitimate routing case) lives at **the same cosine
score as the negative-context false positives**. No threshold can split them:

| threshold | negs filtered? | screenshot still routes? | held-out precision |
|---|---|---|---|
| 0.50 (MiniLM-calibrated) | NO (matched at 0.73-0.76) | yes (0.77) | OK |
| 0.65 | partial | yes | OK |
| 0.87 | YES | yes (barely, 0.63) | **0.53** (dropped 8/17 legit prompts) |

**Conclusion**: e5-large is empirically more accurate (+14 pts on the benchmark
seed) but its denser score distribution means it cannot be a drop-in replacement
at the current single-threshold architecture. Adopting it requires coordinated
changes the project is not ready to make in this slice:

1. **ADR-297 tie-breaker trigger band recalibration**: the current "fire LLM
   tie-breaker when semantic confidence is 0.30-0.55" gate never fires under
   e5-large because almost everything is above 0.55. The band needs to shift
   to e5-large's actual ambiguity zone.
2. **Test architecture pivot**: the negative-context tests assume the matcher
   in isolation catches contextual cues. With a stronger model, that's no
   longer true — tests must exercise the full pipeline (regex + semantic +
   LLM tie-breaker mock) to assert disambiguation correctness.
3. **Operator decision on confidence-band semantics**: with denser scores, the
   `confidence > 0.6` assertion in the ADR-296 acceptance test means something
   different. The mapped-confidence band itself may need a per-model affine.

**Resolution**: keep the calibrated `paraphrase-multilingual-MiniLM-L12-v2`
default. The `COS_SEMANTIC_ROUTING_MODEL` env var remains as the operator escape
hatch for those who want to try e5-large with the documented test-contract
breakage. Phase 2 work is deferred to a future ADR-302 (architectural revisit)
when the team has bandwidth for the coordinated change.

## Rationale

Phase-1 ships the discovery (winner + swap mechanism) without forcing a
calibration cascade. The empirical evidence is preserved in
`routing-benchmark-2026-05-13.md` and reproducible via `cos-routing-benchmark`.
Operators who want the +14 pts now can set the env var; the project's default
stays in its calibrated state until Phase 2 lands the threshold update.

This is intentionally not a "courageous big-bang adoption" decision. The 11
test failures under the swap are a real signal that the system is calibrated to
the current model; flipping the default without re-calibrating the threshold
plus the negative-context test surface would ship a broken contract.

## Operational Guide

### Trying the benchmark winner without committing

```bash
# Per-shell:
export COS_SEMANTIC_ROUTING_MODEL=intfloat/multilingual-e5-large

# Or per-invocation:
COS_SEMANTIC_ROUTING_MODEL=intfloat/multilingual-e5-large python3 -m pytest tests/unit/test_semantic_skill_matcher.py
```

The catalog cache is keyed by `(model_name, skill_corpus_hash)` so the swap
writes to a new cache file under `.cognitive-os/cache/semantic-router/`. No
manual cache invalidation is needed.

### Rolling back to the previous baseline at runtime

Default is already MiniLM. To force it explicitly in an environment that has
been overridden:

```bash
export COS_SEMANTIC_ROUTING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

### Adding new candidates to future benchmark runs

1. Append an entry to `manifests/routing-benchmark-models.yaml` with verified
   upstream license (must be MIT/BSD/Apache).
2. Run `scripts/cos-routing-benchmark --models <new-id>` and review the
   produced report under `docs/06-Daily/reports/routing-benchmark-*.md`.
3. If accuracy beats current default at acceptable p95+memory, file a Phase-2
   ADR with a calibration plan.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Adopt e5-large as default now | Breaks 11 negative-context tests; threshold needs recalibration first. Would ship a broken contract. |
| Keep MiniLM, no benchmark | Defeats the purpose of building ADR-298's harness. Operators have no signal that a +14-pt option exists. |
| Adopt `paraphrase-multilingual-mpnet-base-v2` (Apache, +6 pts) | Strictly dominated by e5-large on accuracy; only wins on latency by a margin (~12 ms) that is well inside the existing budget. Not worth the swap. |
| Adopt e5-large with current 0.50 threshold | Same as bullet 1 — calibration mismatch. |
| Manually re-tune threshold to 0.75 inline | Threshold change is global; touches every consumer of `SemanticSkillMatcher.match`. Coordinated change needs its own slice. |

## Verification

```bash
# Reproduce the benchmark
scripts/cos-routing-benchmark --models baseline-minilm,multilingual-mpnet-base,multilingual-e5-large

# Verify swap mechanism without changing the default
COS_SEMANTIC_ROUTING_MODEL=intfloat/multilingual-e5-large \
    python3 -c "from lib.semantic_skill_matcher import DEFAULT_MODEL_NAME; print(DEFAULT_MODEL_NAME)"
# Expected: intfloat/multilingual-e5-large

# Confirm default is unchanged at import time
python3 -c "from lib.semantic_skill_matcher import DEFAULT_MODEL_NAME; print(DEFAULT_MODEL_NAME)"
# Expected: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```


```bash
python3 -m pytest tests/unit -q
```
## Consequences

- **Operators have a one-env-var path to the +14-pt accuracy upgrade** without
  waiting for Phase 2.
- **The default remains conservative**: existing test contracts and threshold
  calibration are unchanged.
- **The benchmark report is now load-bearing**. Future model-selection ADRs MUST
  cite a `routing-benchmark-*.md` artefact (per ADR-298 contract).
- **bge-m3 / qwen3-embedding / harrier-oss-v1 remain blocked**: their adoption
  requires an ONNX-direct adapter not in FastEmbed's curated registry. Tracked
  as a follow-up.

## Follow-ups

- **ADR-301 candidate**: implement ONNX-direct adapter for HF models not in
  FastEmbed registry (BGE-M3, Qwen3-Embedding-0.6B, Harrier-OSS-v1-270m).
- **Phase 2 of this ADR**: threshold recalibration + negative-context test
  refactor to adopt e5-large as default.
- **Pre-existing**: `test_generic_router_negative_context_rejects_false_positive_cluster[/deep-research]`
  is failing under the strict-xfail mark (matcher matches the criticism-of-skill
  prompt as a positive). Unrelated to this ADR — present in HEAD before this
  change. Likely needs to be split out of `parametrize` or have its xfail
  semantics re-examined.

## Related

- ADR-296 — Language-Agnostic Semantic Routing (the architecture this benchmarks)
- ADR-297 — LLM Tie-Breaker (the designed disambiguator for high-confidence
  semantic matches that this Phase 2 will lean on)
- ADR-298 — Benchmark Harness (the tool that produced the empirical winner)
- ADR-299 — Skill Description Enrichment (the higher-ROI corpus-quality lever
  not exercised in this run)
- `docs/06-Daily/reports/routing-benchmark-2026-05-13.md` — the empirical
  evidence backing this decision

## Evidence

Tier claim evidence is maintained through the boring-reliability control-plane lane:

```bash
scripts/cos-boring-reliability --json
scripts/cos-tier-claim-audit --json
```

This ADR remains `tier: core` because it affects default routing, observability,
or primitive-governance behavior that is part of the core operator control
plane. The tier claim is re-audited by `scripts/cos-tier-claim-audit`.
