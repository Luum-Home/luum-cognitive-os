---
title: "HelixDB Deep Comparison — luum-agent-os vs HelixDB"
date: 2026-05-11
author: orchestrator (research sub-agent)
status: draft
scope: research-only
source-repo: ".cognitive-os/external-source-cache/helix-db/ (shallow clone, helix-db v1.3.3)"
license_constraint: "AGPL-3.0 — pattern-only adoption, clean-room rewrite required"
verdict_runtime: REJECT
verdict_pattern: HOLD / pattern-only
prior_artifacts:
  - docs/research/repo-scout/deep/HelixDB__helix-db-2026-05-11.md
  - docs/reports/external-tools-radar-helixdb-addendum-2026-05-11.md
---

# HelixDB Deep Comparison — luum-agent-os vs HelixDB

> Code-to-code annex set. Verdict was decided in the prior addendum; this set extracts maximum design learning under a pattern-only, clean-room constraint. **No code, no strings, no derivative artifacts.** Every annex describes the pattern in our own words and lists the helix file refs only as evidence — not as a source to copy.

## 1. What HelixDB actually is

HelixDB is a **single-binary Rust graph + vector database** with an integrated DSL compiler and HTTP/MCP gateway. The repo splits into five crates:

| Crate | Role |
|---|---|
| `helix-db/` | Core: storage engine (LMDB via `heed3`), HNSW vector index, BM25 FTS, traversal iterators, HelixQL parser/analyzer/code-generator, HTTP gateway with worker pool, MCP surface. ~580+1037+663+2083 LOC across the load-bearing files. |
| `helix-container/` | The deployable binary. 159 LOC. Boots the gateway, loads inventory-registered handlers and MCP tools (`helix-container/src/main.rs:113-145`). |
| `helix-cli/` | User-facing CLI: `helix init`, `compile`, `push`, `sync`, `deploy`. Contains the **open-core trapdoor** (enterprise-cluster code paths). |
| `helix-macros/` | Proc-macro crate (`#[handler]`, `#[mcp_handler]`) — emits inventory submissions consumed by the container. |
| `metrics/`, `hql-tests/` | Telemetry payload schemas + ~100 HQL conformance fixtures. |

Architecturally interesting properties (all confirmed in source, see annexes for line refs):

1. **HelixQL → Rust compile-to-binary pipeline.** Users write a typed graph-DSL (`.hx` files); `helixc/parser` + `helixc/analyzer` + `helixc/generator` lower it to Rust handler functions that ship inside `helix-container`. There is no query-string runtime path — queries are *only* reachable as compiled endpoints. This is the source of the "secure by default" claim.
2. **Unified primary types: Node / Edge / Vector.** All three are first-class in schema (`N::User { … }`, `E::Follows`, `V::Embedding`); the BM25 inverted index is keyed by the same `u128` doc_id space as nodes.
3. **LMDB-backed everything.** Nodes, edges, in/out edge indices, HNSW layers, BM25 inverted/reverse indices and metadata all live in named tables of one `heed3::Env`. Single ACID surface.
4. **Reader/writer split at the worker level, not the storage level.** LMDB allows N readers + 1 writer; helix runs N worker threads (core-pinned) for reads and a single dedicated writer thread (`helix_gateway/worker_pool/mod.rs:38-72`).
5. **MCP as a *typed traversal sequence*, not free-form prompts.** The MCP tool schema is a strongly-typed enum of traversal steps (`OutStep`, `InStep`, `NFromType`, `SearchVecText`, …) the agent composes — `helix_gateway/mcp/tools.rs:31-83`.

These five properties are the source of every primitive listed in Annex E.

## 2. License posture (binding constraint)

Every artifact in `helix-db/` and `helix-container/` carries `SPDX-License-Identifier: AGPL-3.0` (e.g. `helix-db/src/helixc/parser/mod.rs:1-2`, `helix-db/src/helix_engine/reranker/fusion/rrf.rs:1-2`). The repo `LICENSE` is the full AGPL-3.0 text. Cargo metadata: `helix-db/Cargo.toml:6 license = "AGPL-3.0"`.

Under `rules/license-policy.md`, AGPL-3.0 is **BLOCK**. Consequence: this annex set is **pattern-only**. Each section restates the design pattern in our own words. We do *not* copy line ranges, identifiers, comments, or test fixtures. Any future reimplementation must be a documented clean-room — see Annex D for the procedure.

## 3. Annex map

| Annex | Topic | helix scope | COS comparison |
|---|---|---|---|
| [A](helixdb-annex-a-storage-querycompiler-2026-05-11.md) | Storage layer + HelixQL compile pipeline | `helix-db/src/helix_engine/storage_core/`, `helix-db/src/helixc/{parser,analyzer,generator}/` | Engram SQLite-FTS5 (`lib/engram_*.py`). No DSL-compiler equivalent. |
| [B](helixdb-annex-b-vector-fts-2026-05-11.md) | HNSW vector index + BM25 FTS | `helix-db/src/helix_engine/vector_core/`, `helix-db/src/helix_engine/bm25/`, `reranker/fusion/` | Engram FTS5 + planned LightRAG dual-level slice. |
| [C](helixdb-annex-c-runtime-mcp-2026-05-11.md) | Gateway worker-pool + MCP surface | `helix-db/src/helix_gateway/*`, `helix-container/` | `lib/engram_http_client.py`, COS MCP wiring under `packages/`. |
| [D](helixdb-annex-d-license-opencore-risk-2026-05-11.md) | AGPL §13 + open-core trapdoor evidence | `helix-cli/src/` (enterprise paths), `helix-cli/ENTERPRISE_CLI_TEST_PLAN.md`, `metrics/src/events.rs` | `rules/license-policy.md`, prior addendum. |
| [E](helixdb-annex-e-primitives-2026-05-11.md) | Ranked extractable design patterns | Synthesizes all of the above | COS roadmap alignment table + explicit "do not copy" lines. |

## 4. Top-level verdict (reiterated; not re-litigated)

- **Runtime / dependency**: REJECT. AGPL-3.0 is BLOCK.
- **Pattern lane**: HOLD with high value on a small subset (compiled-DSL contract, typed traversal MCP, reranker fusion taxonomy). Most of the storage/engine work duplicates what we already get from SQLite-FTS5 for the scale Engram operates at.

The 1-line clean-room cost/benefit answer is in Annex E §5.
