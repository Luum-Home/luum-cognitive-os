---
title: "MegaMemory Annex B — In-Process Embeddings (Canonical Port Target)"
date: 2026-05-11
parent: docs/research/megamemory-comparison-2026-05-11.md
source-repo: ".cognitive-os/external-source-cache/MegaMemory (v1.6.2)"
port_target: lib/engram_lifecycle.py (LightRAG dual-level slice)
---

> **License attribution.** Code excerpts and structural descriptions quoted from `0xK3vin/MegaMemory` v1.6.2 (MIT License, Copyright (c) 2026 0xk3vin — see https://github.com/0xK3vin/MegaMemory/blob/main/LICENSE). MIT permits direct vendoring with copyright preservation. See [`megamemory-annex-f-compliance-cleanroom-2026-05-11.md`](megamemory-annex-f-compliance-cleanroom-2026-05-11.md) for the full compliance protocol and port-vs-vendor decisions.

# Annex B — In-Process Embeddings (the canonical port target)

This is the **only** MegaMemory primitive worth porting now. Everything else in MegaMemory either duplicates Engram or is below COS governance/bus-factor floor. This annex pins exactly what the pattern is, why it's better than what we have, and what the Python port looks like.

---

## 1. Source pattern (MegaMemory v1.6.2)

### Full embedding module — `src/embeddings.ts` (122 LoC)

Inspected in its entirety. Three concerns, cleanly separated:

#### a. Lazy-loaded pipeline (`src/embeddings.ts:1-22`)

```ts
import { pipeline, type FeatureExtractionPipeline } from "@xenova/transformers";

const MODEL_NAME = "Xenova/all-MiniLM-L6-v2";
const EMBEDDING_DIM = 384;

let extractor: FeatureExtractionPipeline | null = null;

async function getExtractor(): Promise<FeatureExtractionPipeline> {
  if (!extractor) {
    extractor = await pipeline("feature-extraction", MODEL_NAME, {
      quantized: true,        // ~23MB ONNX, INT8-quantized weights
    });
  }
  return extractor;
}

export async function initializeEmbeddings(): Promise<void> {
  await getExtractor();
}
```

Key properties:

- **Model:** `Xenova/all-MiniLM-L6-v2`, 384-dim, INT8-quantized ONNX. ~23 MB on disk.
- **Runtime:** `@xenova/transformers` v2.17.2 — pure JS ONNX runtime (via `onnxruntime-web` under the hood); **no Python, no GPU, no API key**.
- **Lazy:** singleton extractor initialized on first call; no cold start cost for read-only sessions that don't trigger semantic search.
- **First-time download:** the ONNX file is fetched from Hugging Face on first use into `~/.cache/huggingface/` (or `node_modules/@xenova/transformers/.cache/`). After that, fully offline.

#### b. Embedding generation (`src/embeddings.ts:28-47`)

```ts
export async function embed(text: string): Promise<Buffer> {
  if (!text || text.trim().length === 0) {
    throw new Error(`Cannot embed empty text`);
  }
  const ext = await getExtractor();
  const output = await ext(text, { pooling: "mean", normalize: true });
  const data = output.data as Float32Array;
  const buffer = Buffer.from(data.buffer, data.byteOffset, data.byteLength);

  if (buffer.length !== EMBEDDING_DIM * Float32Array.BYTES_PER_ELEMENT) {
    throw new Error(`Invalid embedding dimension: ...`);
  }
  return buffer;
}
```

- **Pooling:** mean-pooling over token embeddings.
- **Normalization:** L2-normalized at output, so cosine similarity reduces to dot product.
- **Storage:** raw 1536-byte (384 × float32) buffer, stored directly in the `nodes.embedding` BLOB column.
- **Validation:** explicit dimension check on every embed call — defensive coding that pays off when the model registry changes.

#### c. Embedding text composition (`src/embeddings.ts:53-59`)

```ts
export function embeddingText(
  name: string, kind: string, summary: string
): string {
  return `${kind}: ${name} — ${summary}`;
}
```

A field-aware concatenation pattern: prepending the `kind` biases the embedding space toward type-clustering. **Worth preserving in the port** — Engram observations have a comparable composition (`type`, `title`, `content`).

#### d. Cosine search loop (`src/embeddings.ts:65-120`)

```ts
export function cosineSimilarity(a: Buffer, b: Buffer): number {
  const vecA = new Float32Array(a.buffer, a.byteOffset, a.byteLength / 4);
  const vecB = new Float32Array(b.buffer, b.byteOffset, b.byteLength / 4);
  if (vecA.length !== vecB.length) throw new Error("dim mismatch");

  let dot = 0, normA = 0, normB = 0;
  for (let i = 0; i < vecA.length; i++) {
    dot += vecA[i] * vecB[i];
    normA += vecA[i] * vecA[i];
    normB += vecB[i] * vecB[i];
  }
  const denom = Math.sqrt(normA) * Math.sqrt(normB);
  return denom === 0 ? 0 : dot / denom;
}

export function findTopK(queryEmbedding, candidates, topK): ... {
  const scored = candidates
    .filter((c) => c.embedding !== null && c.embedding.length > 0)
    .map((c) => ({ id: c.id, similarity: cosineSimilarity(queryEmbedding, c.embedding!) }))
    .sort((a, b) => b.similarity - a.similarity);
  return scored.slice(0, topK);
}
```

Naïve linear scan. **At <10k nodes this is fine.** No ANN index (FAISS / HNSW). The simplicity is deliberate: no extra dependencies, no rebuild costs, no index-versus-WAL coordination.

This linear-scan-with-normalized-vectors pattern is the **canonical small-corpus baseline**. Above ~50k vectors we'd want HNSW; below, the simpler code dominates.

### Where it's called from

- `src/tools.ts:109-137` (`understand`): embeds the query, fetches all active nodes with embeddings, calls `findTopK`.
- `src/tools.ts:150-191` (`createConcept`): embeds `embeddingText(name, kind, summary)` and stores it in the same INSERT.
- `src/tools.ts:193-223` (`updateConcept`): re-embeds when `name`, `kind`, or `summary` change.
- `src/tools.ts:354-410` (`resolveConflict`): re-embeds the resolved concept after a merge resolution.
- `src/web.ts:9` (`initializeEmbeddings`): warm the model when the explorer starts.

The embedding model is exercised on every write path that touches a semantic field. **Embedding is a non-optional first-class field**, not a sidecar. That's the architectural decision worth absorbing.

---

## 2. Engram's current state

- `lib/engram_lifecycle.py` (~~/lib/engram_lifecycle.py:299-361~~) implements `search()` with **FTS5-only** ranking plus a `graph_walk=True` BFS step that joins via `memory_relations`.
- No `embedding` column exists on `observations` today. No in-process embedder is wired in.
- The optional Cognee HTTP integration (`lib/cognee_client.py`) is the only path to vector recall, and it is an external dependency with its own runtime.
- The LightRAG dual-level slice is **planned but not implemented** (`docs/architecture/memory-layer-evolution-sdd.md:84`, `docs/reports/cross-check-A-memory-2026-05-08.md` §LightRAG).

The MegaMemory primitive plugs into precisely the gap LightRAG needs filled: a no-key, no-network, low-footprint sentence embedder that lives in the same process as the memory store.

---

## 3. Verdict for the port

| Dimension | MegaMemory | Engram (today) | Engram (LightRAG-slice plan) | Verdict |
|---|---|---|---|---|
| In-process semantic recall | Yes | No (FTS5 only) | Planned | **MEJOR_EXTERNO** today; closes once LightRAG slice lands. |
| API-key dependency | None | None (FTS5) or Cognee daemon | TBD | MegaMemory's no-key path is the bar to clear. |
| Model footprint | ~23 MB ONNX, INT8 quantized | n/a | TBD | MiniLM is a known-good default for sentence-level recall. |
| Storage shape | `embedding BLOB` next to row | n/a | `observations.embedding BLOB` planned | MegaMemory confirms the shape works. |
| Top-K algorithm | Linear scan over normalized float32 | n/a | Same baseline expected | Adequate at COS-scale Engram corpora today (<5k observations per project). |
| Field-aware text composition | `${kind}: ${name} — ${summary}` | n/a | Type-prefixed composition for observations | Worth porting verbatim (pattern, not literal string). |

---

## 4. Python port plan

### 4.1 Dependency choice

**Primary:** `sentence-transformers` (Apache-2.0).

- Wraps the same `all-MiniLM-L6-v2` checkpoint.
- Native float32 output, mean-pooled and L2-normalized by default (`normalize_embeddings=True`).
- Requires `torch` (CPU build is ~150 MB wheel) and `transformers`.
- Trade-off: heavier dependency footprint than the JS ONNX runtime, but it is the de-facto Python sentence-embedding library and integrates cleanly with `numpy`.

**Alternative (lighter, recommended for Engram daemon):** `fastembed` (Apache-2.0).

- Pure ONNX runtime via `onnxruntime` (the same engine Xenova uses under the hood in JS).
- Ships with quantized `all-MiniLM-L6-v2` out of the box.
- No `torch` dependency, ~15 MB Python runtime + ~23 MB ONNX model.
- API: `TextEmbedding("sentence-transformers/all-MiniLM-L6-v2-quantized")` → `.embed(text)` yields `np.ndarray`.

**Recommendation:** `fastembed` for closer dependency-footprint parity with MegaMemory. Fallback to `sentence-transformers` if `fastembed` model coverage gaps appear in production.

### 4.2 Module shape (Python equivalent)

Target file: new `lib/engram_embedder.py`, called from `lib/engram_lifecycle.py`.

```python
# lib/engram_embedder.py (proposed)

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
_LOCK = threading.Lock()
_MODEL = None  # lazy


def _model_cache_dir() -> Path:
    # Honor HF_HOME / XDG_CACHE_HOME conventions; default to .cognitive-os/cache/embeddings.
    ...


def _load_model():
    global _MODEL
    if _MODEL is None:
        with _LOCK:
            if _MODEL is None:
                from fastembed import TextEmbedding
                _MODEL = TextEmbedding(MODEL_NAME, cache_dir=str(_model_cache_dir()))
    return _MODEL


def embed(text: str) -> np.ndarray:
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")
    model = _load_model()
    [vec] = list(model.embed([text]))  # already normalized
    assert vec.shape == (EMBEDDING_DIM,), f"unexpected dim: {vec.shape}"
    return vec.astype(np.float32)


def embedding_text(obs_type: str, title: str, content: str) -> str:
    # Mirror MegaMemory's field-aware composition for type-clustering.
    return f"{obs_type}: {title} — {content[:1024]}"


def cosine_top_k(query: np.ndarray, candidates: Sequence[tuple[str, np.ndarray]], k: int):
    # Vectors are L2-normalized → cosine = dot product.
    if not candidates:
        return []
    ids = [c[0] for c in candidates]
    matrix = np.stack([c[1] for c in candidates])
    sims = matrix @ query
    top_idx = np.argsort(-sims)[:k]
    return [(ids[i], float(sims[i])) for i in top_idx]
```

### 4.3 Storage strategy

- Add an `embedding BLOB` column to `observations` (Engram migration, version-bumped).
- Encode as raw `float32` little-endian bytes (`vec.tobytes()`) — 1536 bytes per row.
- Decode on read with `np.frombuffer(blob, dtype=np.float32)`.
- Backfill: a one-shot script iterating existing observations under the new feature flag.

### 4.4 Model cache strategy

- Default cache: `${COS_HOME}/.cognitive-os/cache/embeddings/` (per `RULES-COMPACT.md` engram-organization).
- Honor `HF_HOME` and `XDG_CACHE_HOME` if set.
- First load logs the cache path + download size at WARN level so operators see the ~23 MB fetch.
- **No automatic re-download** if the file exists and matches expected size.

### 4.5 Lazy-load policy

- Module-level lazy singleton with a double-checked lock (`threading.Lock`).
- Embedder NOT loaded at Engram daemon startup; loaded only on the first `search(use_embeddings=True)` or `save(with_embedding=True)` call.
- Cold-start budget: **<2 s** on COS workstation profiles (per the existing addendum acceptance criterion).

### 4.6 Fallback policy (model unavailable / disabled)

Feature flag: `engram.embeddings.enabled` (default `false` until the LightRAG slice ships).

Failure cases and response:

1. **Flag off** → never load model; `search()` falls back to FTS5-only path.
2. **`fastembed` not installed** → log WARN once, set runtime flag off, fall back.
3. **Model download fails** (offline first run) → raise `EmbedderUnavailable`, caught at the search boundary, fall back to FTS5, surface a one-line operator notice.
4. **Dimension mismatch on load** → fail loud; this is corruption, not a degradation.

### 4.7 License verification

The `Xenova/all-MiniLM-L6-v2` weights on HF derive from `sentence-transformers/all-MiniLM-L6-v2`, which is **Apache-2.0**. This must be re-verified at port time:

- Confirm model card license at port time (HuggingFace page + the `huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/README.md`).
- Confirm `fastembed` quantized variant license matches.
- Record the verified license + model digest in `manifests/external-tools-adoption.yaml` under a new `embedding-models` section.

`@xenova/transformers` itself is **Apache-2.0** (verified on its npm package page) — useful as a sanity check but irrelevant to the Python port (we do not import it).

### 4.8 Dependency footprint summary

| Component | Size | License | Notes |
|---|---:|---|---|
| `fastembed` Python package | ~5 MB | Apache-2.0 | Pulls in `onnxruntime` (~30 MB). |
| `onnxruntime` (CPU) | ~30 MB | MIT | Production-grade, x86-64 + ARM64. |
| `all-MiniLM-L6-v2` ONNX quantized | ~23 MB | Apache-2.0 | One-time download. |
| `numpy` | already a transitive dep | BSD | — |
| **Total new on-disk cost** | **~60 MB** | All ALLOW | Lower than `sentence-transformers + torch` (~200+ MB). |

---

## 5. Acceptance criteria (from the radar addendum, restated)

Port is **accepted** only if all of:

1. Cold start <2 s on the project Engram corpus.
2. Embedding model artifact tracked in `manifests/external-tools-adoption.yaml` with verified license + digest.
3. Dual-level (entity + topic) scoring measurably ≥10% better than FTS5-only on a semantic-recall A/B on existing Engram observations, **or the port is reverted**.
4. No new MCP server registered. No new SQLite store. Engram remains the single memory plane.
5. `judgment_required` / `mem_judge` semantics unchanged.

---

## 6. Vendor-vs-port decision

| Option | Verdict |
|---|---|
| Vendor `src/embeddings.ts` verbatim | **REJECT.** Different runtime (TS/Node vs Python). |
| Vendor with attribution | **REJECT.** Trivially short, idiomatic Python rewrite is cleaner and audit-friendlier. |
| Re-implement from pattern + attribute | **ACCEPT.** Cite the MegaMemory file in the port doc; record the attribution in `manifests/external-tools-adoption.yaml`. |

The pattern is small enough that vendoring saves nothing and obscures the dependency graph.

---

## 7. Time estimate

3–5 working days for the Python port + Engram migration + feature flag + backfill + A/B harness, assuming `fastembed` works out-of-the-box and the LightRAG dual-level scorer is a separate slice. **Open this only when the LightRAG SDD reaches the dual-level retrieval phase**, not before — the embedder without the dual-level algorithm is half a feature.
