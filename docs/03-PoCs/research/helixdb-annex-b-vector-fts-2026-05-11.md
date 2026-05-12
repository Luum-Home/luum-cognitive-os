---
title: "HelixDB Annex B — Vector (HNSW) & full-text (BM25) indexing + reranker fusion"
date: 2026-05-11
parent: helixdb-comparison-2026-05-11.md
scope: research-only
license_constraint: "AGPL-3.0 — pattern-only adoption, clean-room rewrite required. No code, identifiers, comments or test fixtures may be reused."
---

> **License compliance disclaimer.** Structural descriptions and value references in this annex are paraphrased from upstream HelixDB (AGPL-3.0, https://github.com/HelixDB/helix-db). No verbatim source code is vendored into COS — code-block fences contain pseudo-syntax sketches, factual config values, or API surface enumerations that are non-creative or fair-use. Clean-room rewrites of any documented primitive MUST reference these annexes as **inputs**, not derive directly from upstream source. See [`helixdb-annex-d-license-opencore-risk-2026-05-11.md`](helixdb-annex-d-license-opencore-risk-2026-05-11.md) for the full license disposition (REJECT runtime / TRIAL-PATTERNS clean-room-only).

# Annex B — Vector + FTS indexing & reranker fusion

## B.1 HNSW implementation

### Configuration (`helix-db/src/helix_engine/vector_core/vector_core.rs:31-62`)

```
HNSWConfig {
    m,             // bi-directional links per element
    m_max_0,       // max links for layer 0 (= 2 × m)
    ef_construct,  // dynamic candidate list size at construction
    m_l,           // level-generation factor (= 1 / ln(m))
    ef,            // candidate list at search
    min_neighbors, // = 512 always
}
```

Defaults and clamps (`:48-61`):
- `m = 16`, clamped to `[5, 48]`.
- `ef_construct = 128`, clamped to `[40, 512]`.
- `ef = 768` default — **but** clamped to `[10, 512]` so the effective default ends up as 512. The default of 768 is dead code; this is almost certainly a bug worth noting (see Annex G-style finding §B.5).
- `m_l = 1.0 / ln(m)` (Malkov & Yashunin original recipe).

### Trait surface (`helix-db/src/helix_engine/vector_core/hnsw.rs:1-62`)

Three methods only:
- `search(txn, query, k, label, filter, should_trickle, arena) -> Vec<HVector>`
- `insert(txn, label, data, properties, arena) -> HVector`
- `delete(txn, id, arena) -> ()`

Both `search` and `insert` carry a generic filter `F: Fn(&HVector, &RoTxn) -> bool` — the index is filter-aware, **not** filter-after-knn. The filter is consulted *during* the level traversal, not as a post-filter (see `vector_core.rs:166-217` `get_neighbors` and `:312-381` `search_level`). This is the right way; many vector DBs (early Pinecone, Chroma <0.5) post-filter, which collapses recall when the filter is selective.

### Persistence layout

`vector_core.rs:24-26` and `:91-112`:
- `DB_VECTORS = "vectors"` — keyed `[v: ‖ u128_id ‖ usize_level]`. Encodes vector body per (id, level).
- `DB_VECTOR_DATA = "vector_data"` — `u128 → Bytes`, property payload.
- `DB_HNSW_EDGES = "hnsw_out_nodes"` — `[u128_src ‖ usize_level ‖ u128_sink] → Unit`. Adjacency lives as keys, not values; lookup is by prefix scan.
- `ENTRY_POINT_KEY = b"entry_point"` — single fixed key for the top-layer entry vertex.

### Distance metrics

`helix-db/src/helix_engine/vector_core/vector_distance.rs` defines them; the `cosine` Cargo feature (`helix-db/Cargo.toml:79 cosine = []`) gates the default. SIMD acceleration: not observed in the cloned source — distance is plain Rust loops over `&[f64]`. Vectors are `f64`, not `f32` (see `hnsw.rs:18 query: &'arena [f64]`) — that doubles memory vs the more common `f32` choice and rules out using `bytemuck` casts to GPU types.

### Pattern (clean-room description)

> A standard HNSW index with M/efConstruction/ef parameters, layered on a key/value store via prefix-keyed adjacency. Filter callbacks are passed into the level-walk so selectivity does not collapse recall. `f64` precision throughout. Adjacency persisted as keys (zero-byte values) — a small space/lookup-cost trade.

## B.2 BM25 full-text index

### Tables (`helix-db/src/helix_engine/bm25/bm25.rs:21-25`)

| Table | Key → Value | Purpose |
|---|---|---|
| `bm25_inverted_index` | `term_bytes → PostingListEntry` (DUP_SORT) | term → list of (doc_id, tf). |
| `bm25_reverse_index` | `u128 doc_id → ReversePostingEntry` (DUP_SORT) | doc_id → list of (term, tf). Enables O(doc_terms) delete. |
| `bm25_doc_lengths` | `u128 → u32` | per-doc length. |
| `bm25_term_frequencies` | `term_bytes → u32` | document frequency for the term. |
| `bm25_metadata` | fixed keys | total_docs, avgdl, k1, b. |

Schema version is tracked at `bm25.rs:27-28` (`BM25_SCHEMA_VERSION = 2`). The metadata payload `BM25Metadata { total_docs, avgdl, k1, b }` is bincode-serialized (`:30-36`).

### Tokenizer (`bm25.rs:785-791`)

Trivial: lowercase, split on `!c.is_alphanumeric()`, drop empties, drop ≤2-char tokens iff the const-generic `SHOULD_FILTER` is true. **No stemming, no stopwords, no language detection.** That is honest — many BM25 impls bundle Porter stemming and harm recall on non-English text.

### Insert / update / delete

`bm25.rs:793-829`:
- `insert_doc` rejects duplicate ids (`:794-798`). Computes term counts, builds `Vec<ReversePostingEntry>`, derives doc length from sum of tfs, writes both indices + length + tf increments in one txn.
- `delete_doc` walks the reverse index first, then decrements each posting in the inverted index. The reverse index is the *only* reason this is O(distinct_terms_in_doc) rather than full-scan.
- `update_doc` = compute new reverse entries, diff against old via `update_doc_with_reverse_entries` (defined earlier in file). Idempotent recompute, not an in-place diff at the term level beyond what bincode allows.

### Score formula (`bm25.rs:831-857`)

Standard Robertson/Sparck-Jones BM25:
- `idf = ln(((N - df + 0.5) / (df + 0.5)) + 1)` — the +1 inside the log is the **Lucene variant** (always non-negative). Comment at `:843-845` acknowledges that *without* +1 IDF can be negative, which is "mathematically correct" — they chose the safe variant.
- `tf_component = tf * (k1 + 1) / (tf + k1 * (1 - b + b * doc_len / avgdl))`.
- `k1`/`b` defaults: not visible at this offset; check `HBM25Config::new`. Per `BM25Metadata`, they are `f32` (`:34-35`) — precision loss vs typical f64 BM25 but irrelevant at retrieval scale.

### Search (`bm25.rs:859-…`)

`search(txn, query, limit, arena)`:
- Tokenizes with `SHOULD_FILTER = true`.
- Reads metadata; bails on `total_docs == 0`.
- Pre-allocates a score `HashMap<u128, f32>` sized `min(query_terms × 50, limit × 4)` (`:882-883`) — a small but real micro-optimization.
- For each term: looks up df; if 0 skip; otherwise iterates `get_duplicates` on the inverted index to walk every posting in O(matching_docs).
- Returns `Vec<(u128, f32)>` (truncated to limit by the caller).

### Pattern (clean-room description)

> Two-way inverted index (term→postings + doc→terms) keyed in dup-sort tables. Tokenizer is dumb-on-purpose. Score uses the Lucene non-negative IDF variant. The reverse index makes deletes term-local instead of scan-the-world.

## B.3 Reranker fusion (RRF + MMR)

The repo includes a real reranker layer at `helix-db/src/helix_engine/reranker/` — not just a vector + FTS bolt-together. Two fusion strategies live under `fusion/`:

### RRF — Reciprocal Rank Fusion (`reranker/fusion/rrf.rs:1-50+`)

- Default `k = 60` (the published Cormack/Clarke/Buettcher value).
- Formula in comments: `RRF_score(d) = Σ 1/(k + rank_i(d))`.
- Constructor `with_k(k)` rejects non-positive k (`:38-44`).
- Score-source agnostic — combines multiple ranked lists without calibration. This is the *correct* default for hybrid (BM25 ⊕ vector) where the score scales are non-commensurable.

### MMR — Maximal Marginal Relevance (`reranker/fusion/mmr.rs:1-50+`)

- `lambda ∈ [0, 1]` (default 0.7 favouring relevance, `:48-49`).
- Distance method enum: `Cosine | Euclidean | DotProduct`.
- Carries an optional `query_vector` for relevance term; iterates greedy selection.

### Score normalizer

`reranker/fusion/score_normalizer.rs` exists and is referenced; it provides shared min-max / softmax scaling. Useful only when calibrated fusion is desired (not RRF's case).

### Pattern (clean-room description)

> Hybrid retrieval is not a join of vector + FTS results; it is an *explicit reranker layer* with at minimum RRF (calibration-free) and MMR (diversity-aware) strategies. Score-normalizer is separated from rerankers so calibration is opt-in.

## B.4 Comparison with COS

| Concern | HelixDB | luum-agent-os (Engram) |
|---|---|---|
| Vector index | Filter-aware HNSW over `f64` | Not present in shipped Engram. SDD work on memory-layer evolution exists (`docs/04-Concepts/architecture/memory-layer-evolution-sdd.md`). |
| Full-text | Custom BM25 over LMDB | **SQLite FTS5** (built into `lib/engram_client.py`) — gets us BM25 + tokenizer + porter stemmer + Unicode for free, with zero index-maintenance code. |
| Hybrid fusion | RRF + MMR rerankers | Not present. The planned **LightRAG dual-level slice** would need a fusion layer if it ships. |
| Diversity (MMR) | Built-in | Not present. |
| Tokenizer | Lowercase + alphanumeric split + ≥3-char filter (no stemming) | FTS5 `porter`/`unicode61` — much stronger out of box. |
| Schema versioning | `BM25_SCHEMA_VERSION = 2` constant + metadata table | FTS5 schema migrations handled at SQLite level. |

### What COS could borrow (deferred to Annex E)

- The **two-way (forward + reverse) inverted-index** pattern (Primitive #4). FTS5 already provides this internally but exposes only the forward direction; *if* we ever build a custom index for Engram crystallization, we want the reverse index so deletes stay cheap.
- **RRF + MMR as a separate reranker layer** (Primitive #3). This is the most directly portable design and aligns with planned hybrid retrieval.
- **Filter-aware HNSW search** (vs post-filter) — a contract requirement, not necessarily a HelixDB-specific design.

### What is *not* applicable

- A custom BM25 reimplementation. FTS5 wins on every axis (correctness, multilingualism, ops cost).
- An `f64` HNSW. We have no use-case requiring f64 precision; `f32` would halve memory.
- LMDB-keyed adjacency for the index. SQLite or a flat file beats it for our scale.

## B.5 Surprise finding

`HNSWConfig::new` at `vector_core/vector_core.rs:48-61`:
```
ef = 768 default, .clamp(10, 512)
```
The default of 768 is silently downgraded to 512 by the clamp; the value 768 never reaches the rest of the system. Either the default or the clamp upper bound is wrong.

**Upstream observation only.** HelixDB is REJECT runtime per AGPL-3.0; Engram retains SQLite — no COS HNSW implementation is planned. If the AGPL disposition ever reverses, file this inconsistency upstream with HelixDB. See annex E §E.4.5 sidebar and `docs/03-PoCs/research/orchestrator-self-critique-cluster-d-claim-quality-2026-05-11.md` Finding 10 for the cluster-D ruling that scopes this observation.

## B.6 Clean-room constraint

- Re-derive BM25 from the literature, not from `bm25.rs`.
- The HNSW algorithm is published (Malkov & Yashunin, 2016); re-derive parameters from the paper.
- For RRF and MMR, the formulas are textbook; cite the original papers (Cormack et al. 2009, Carbonell & Goldstein 1998) in the COS-side ADR.
- Do not transcribe table names, key prefixes (`v:`, `bm25_*`, `hnsw_out_nodes`), or default constants from helix source. Choose new ones.
