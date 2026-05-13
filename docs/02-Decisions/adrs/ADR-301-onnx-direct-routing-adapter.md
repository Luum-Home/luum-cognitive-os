---
adr: 301
title: ONNX-Direct Routing Adapter — Generic HF-Hosted ONNX Bi-Encoder Loader
status: accepted
implementation_status: implemented
date: '2026-05-13'
supersedes: []
superseded_by: null
extends:
  - ADR-298
  - ADR-300
implementation_files:
  - lib/routing_benchmark.py
  - manifests/routing-benchmark-models.yaml
  - tests/unit/test_routing_benchmark_onnx_adapter.py
  - docs/06-Daily/reports/routing-benchmark-2026-05-13.md
tier: core
tags:
  - skill-router
  - benchmark
  - onnx
  - adapter
  - model-selection
verification_level: medium
classification_basis: |
  Adapter ships with unit tests (protocol conformance, license gate, lazy-load,
  revision-aware cache, graceful HF 404). End-to-end smoke validated by running
  the harness against BAAI/bge-m3 and updating the comparison report.
---

# ADR-301: ONNX-Direct Routing Adapter

## Status

Accepted — 2026-05-13.

## Context

ADR-298 built the routing-model benchmark harness. ADR-300 ran it and crowned
`intfloat/multilingual-e5-large` (precision@1 = 0.897). The harness had ONE
adapter — `FastembedBiEncoderAdapter` — which only loads models that appear in
`fastembed.TextEmbedding.list_supported_models()`.

`BAAI/bge-m3`, `Qwen/Qwen3-Embedding-0.6B`, and `microsoft/harrier-oss-v1-270m`
are NOT in FastEmbed's curated registry, but their ONNX weights are publicly
hosted on HuggingFace under permissive licenses (MIT / Apache-2.0). ADR-300
explicitly deferred a generic ONNX adapter to a follow-up ADR — this is it.

The immediate driver is BGE-M3: a candidate that may dethrone the current
e5-large winner (BGE-M3 is the historical multilingual retrieval reference;
e5-large is newer but comparable size). Without an ONNX-direct path we cannot
even measure it, which means model selection is artificially constrained to
FastEmbed's catalog.

## Decision

Add a generic `OnnxDirectBiEncoderAdapter` to `lib/routing_benchmark.py` that:

1. **License-gates first.** No download attempted before
   `enforce_license_gate` succeeds — same gate as every other adapter.
2. **Lazy-downloads** model + tokenizer files from any HF repo via
   `huggingface_hub.hf_hub_download`. Construction does no I/O — only
   `.load()` triggers network.
3. **Runs inference via `onnxruntime`** (`CPUExecutionProvider`). Mean-pools
   the last hidden state with attention-mask weighting and L2-normalises —
   identical embedding contract to the FastEmbed adapter.
4. **Revision-aware caches** under
   `.cognitive-os/cache/onnx-models/<sha256(model_name+revision)>/` so that
   `revision: main` and a pinned commit SHA never collide.
5. **Fails gracefully.** A 404 / network error during `.load()` is caught by
   the harness and surfaced as a clean `load_failure` row in the report,
   never an exception that aborts the run.

Manifest entries opt in by setting `adapter: onnx-direct-bi-encoder`. They MAY
specify `onnx_subpath` (default `model.onnx`) and `revision` (default `main`).

## Migration

Any model whose weights are publishable as ONNX on HuggingFace and whose
license is in the MIT/BSD/Apache permit-list can be added to
`manifests/routing-benchmark-models.yaml` with adapter
`onnx-direct-bi-encoder`. No code change required per new model.

The first migration in this ADR: the existing `bge-m3` entry switches from
`fastembed-bi-encoder` (which load-failed in ADR-300) to
`onnx-direct-bi-encoder` with `onnx_subpath: onnx/model.onnx` (verified
against `BAAI/bge-m3` HF tree). Tokenizer files co-located in the same `onnx/`
directory.

Qwen3-embedding and harrier-oss are deliberately left untouched — they are
follow-up candidates once the BGE-M3 vs e5-large measurement lands.

## Verification

`docs/06-Daily/reports/routing-benchmark-2026-05-13.md` is the artefact. It
shows `bge-m3` loaded via the new adapter alongside the three FastEmbed
candidates from ADR-300. Whichever model tops precision@1 in the regenerated
report is the new ADR-300 candidate winner. Selection-policy changes (i.e.
making BGE-M3 the production matcher) require a follow-up ADR — this one
only delivers the measurement capability.

## Risks

- **Disk footprint.** Each new ONNX model is ~2 GB. The cache is opt-in
  (only downloaded when the adapter loads) and revision-keyed so stale
  revisions can be GC'd manually. No automatic eviction in this ADR.
- **Tokenizer drift.** We rely on the model's own `tokenizer.json`. If a
  repo ships an incomplete tokenizer config, `.load()` fails cleanly — but
  the failure surfaces as `load_failure` rather than as a silent accuracy
  regression. Mitigation: the unit test suite includes a load-failure path
  and the harness is unaffected by single-model load failures.
- **External-data files.** Some HF repos (BGE-M3 included) split ONNX
  weights into `model.onnx` + `model.onnx_data`. The adapter downloads the
  sibling `.onnx_data` file when present so onnxruntime can resolve the
  external initialisers.
