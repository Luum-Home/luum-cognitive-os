---
title: "HelixDB Annex A — Storage core & HelixQL query compiler"
date: 2026-05-11
parent: helixdb-comparison-2026-05-11.md
scope: research-only
license_constraint: "AGPL-3.0 — pattern-only adoption, clean-room rewrite required. No code, identifiers, comments or test fixtures may be reused."
---

# Annex A — Storage core & HelixQL query compiler

## A.1 Storage core (LMDB via heed3)

### Layout

`helix-db/src/helix_engine/storage_core/mod.rs:38-68` declares the database surface. One `heed3::Env` (LMDB environment) hosts 5 named base tables plus N dynamic ones:

| Table constant (line) | Key → Value | Purpose |
|---|---|---|
| `DB_NODES` (`:39`) | `u128 → Bytes` | Node payload, big-endian id key. |
| `DB_EDGES` (`:40`) | `u128 → Bytes` | Edge payload. |
| `DB_OUT_EDGES` (`:41`) | `(from_id ‖ label_hash) → (edge_id ‖ to_id)` | Outgoing adjacency. Uses LMDB `DUP_SORT + DUP_FIXED` (see comment at `:114-118`) — single fixed-size value pack per duplicate key, no 8-byte length header. |
| `DB_IN_EDGES` (`:42`) | mirror of out | Incoming adjacency. |
| `DB_STORAGE_METADATA` (`:43`) | `Bytes → Bytes` | Version info, schema hash, embedding model id. |

Plus dynamic tables: per-indexed-field secondary indices (`secondary_indices: HashMap<String, (Database<Bytes, U128<BE>>, SecondaryIndex)>` at `:61`), three vector tables (`v:`, `vector_data`, `hnsw_out_nodes` — see `helix-db/src/helix_engine/vector_core/vector_core.rs:24-26`), and five BM25 tables (`helix-db/src/helix_engine/bm25/bm25.rs:21-25`). All inside the same `Env` → one ACID transaction spans graph + vector + FTS.

### Configuration

`HelixGraphStorage::new` at `storage_core/mod.rs:71-105`:
- `map_size = db_max_size_gb (default 100, capped at 9998) × 1 GiB`.
- `max_dbs = 200`, `max_readers = 200`.
- `EnvOpenOptions::new()` called in `unsafe` block — LMDB mmap is intrinsically unsafe in Rust's model (other processes can mutate the file).

### Concurrency / MVCC

LMDB itself provides MVCC + copy-on-write B-trees. Helix sits on top, not under, that model — the interesting design choice is **how it splits readers from the writer at the application layer** rather than letting heed do it implicitly:

- N reader workers + 1 dedicated writer worker (`helix-db/src/helix_gateway/worker_pool/mod.rs:21-72`, see Annex C).
- Mutating handlers are tagged at proc-macro time (`#[handler(is_write)]` — emitted at `helix-db/src/helixc/generator/queries.rs:25-29`). The router consults `write_routes: HashSet<String>` (`helix_gateway/worker_pool/mod.rs:89-94`) to dispatch to the writer channel.
- Net effect: write contention is serialized at the channel level **before** touching LMDB, eliminating LMDB-level writer-lock thrash.

### Traversal iterators

`helix-db/src/helix_engine/traversal_core/traversal_iter.rs:11-152` defines `RoTraversalIterator<'db, 'arena, 'txn, I>` and a mirrored `Rw…` variant. Two design notes:

1. **Three lifetime parameters** (`'db ⊇ 'arena ⊇ 'txn`) thread the LMDB-borrow lifetime through the iterator chain. Each pipeline step (`out_e`, `in_`, `filter`, `range`, …) returns a new `RoTraversalIterator<…, NewI>` parameterized on the wrapped iterator. The borrow checker therefore guarantees you cannot keep an LMDB byte-slice alive past the transaction.
2. **Bumpalo arena (`bumpalo::Bump`) for per-query allocation.** All `BVec`/`BString` returned from a traversal live in the arena, dropped wholesale at end of query. Visible at the BM25 search signature `helix-db/src/helix_engine/bm25/bm25.rs:85-91`, the HNSW search return `bumpalo::collections::Vec<'arena, HVector<'arena>>` (`vector_core/hnsw.rs:18-31`), and across the traversal-ops modules under `helix_engine/traversal_core/ops/`.

### Pattern (clean-room description)

> A single mmap-backed key/value substrate hosts (a) graph adjacency in dup-sorted dup-fixed tables, (b) vector layers under prefix-typed keys, (c) inverted-index posting lists, and (d) per-field secondary indices, all sharing one ACID transaction boundary. Concurrency is funneled through an application-level writer channel; readers go directly into MVCC snapshots. Iterators are typed and carry the txn lifetime so query results cannot outlive the snapshot.

## A.2 HelixQL compiler

The compiler is a three-stage pipeline, all under `helix-db/src/helixc/`:

### Stage 1 — Parser (`helixc/parser/`)

- Grammar declared via `pest_derive::Parser` from `helixc/parser/mod.rs:32-34` referencing a Pest grammar file `grammar.pest` (loaded by `#[grammar = …]`).
- `HelixParser::parse_source` (`mod.rs:39-202`) accepts `Content { files: Vec<HxFile>, … }` (multi-file project; `parser/types.rs:14-26`) and produces a `Source { schema: HashMap<usize, Schema>, migrations, queries }` — the `HashMap<usize, _>` keyed by schema version is how migrations are tracked.
- Three first-class top-level constructs: `Rule::schema_def`, `Rule::migration_def`, `Rule::query_def` (`mod.rs:67-160`). Queries are deferred to a second pass after schemas are resolved — note `remaining_queries: HashSet<…>` at `:63-65`.

### Stage 2 — Analyzer (`helixc/analyzer/`)

`helixc/analyzer/mod.rs:36-42` is the entry point. Three passes:

1. `check_schema` — validates edge endpoints refer to declared nodes (`analyzer/methods/schema_methods.rs`).
2. `check_schema_migrations` — per-version migration validation.
3. `check_queries` — type-checks every query against the schema field-lookup tables built once at `:71-72`.

Key data structures (`analyzer/mod.rs:54-66`):
- `node_set / vector_set / edge_map` — schema-name lookups.
- `node_fields / edge_fields / vector_fields: IndexMap<&str, IndexMap<&str, Cow<Field>>>` — field tables. Note **`IndexMap`** (insertion-order preserving) is chosen over `HashMap` — generated Rust code therefore has stable field ordering across builds.
- `secondary_indices: Vec<SecondaryIndex>` — derived from `is_indexed()` flags on schema fields (`analyzer/mod.rs:75-82`).
- `IntrospectionData` (`mod.rs:166-180`) — emitted as serializable JSON so the HTTP gateway can self-describe its API to MCP clients (handler defined in `helix_gateway/introspect_schema.rs`).

Errors flow through `Diagnostic` (`analyzer/diagnostic.rs`) with `ariadne` for pretty-printing (`Cargo.toml:38 ariadne = { version = "0.5", optional = true }`, gated behind the `compiler` feature).

### Stage 3 — Generator (`helixc/generator/`)

`helixc/generator/queries.rs:9-21` defines the `Query` AST emitted by the analyzer. The `Display for Query` impl (`:2039`) is the **code emitter** — it writes Rust source to a `fmt::Formatter`. Concretely, for each HelixQL query the generator emits:

- An `<Name>Input` `#[derive(Serialize, Deserialize, Clone)]` struct (`:59-73`).
- Sub-parameter structs (`:32-42`).
- Return-value structs (`:44-57`, new path) or a `json!` macro literal (legacy path; switch at `:164-166`).
- A handler function with the signature `pub fn <name>(input: HandlerInput) -> Result<Response, GraphError>` (`:122-124`), with `#[handler(is_write)]` annotation iff the query mutates (`:24-30`).
- Boilerplate: `let db = Arc::clone(&input.graph.storage); … let arena = Bump::new(); let txn = db.graph_env.{read,write}_txn()?;` (`:127-156`) — read vs write txn chosen from the same `is_mut` flag.
- Each statement converted to a Rust line via `Statement: Display` (`generator/statements.rs`).

Embedding calls are *hoisted* (`print_hoisted_embedding_calls`, `:75-100`): an async embedding RPC happens **before** the LMDB transaction opens, so the transaction never blocks on a network call. This is a quietly important pattern.

Output files are placed by the CLI under a `queries_project_dir` and a `queries.json` manifest is emitted (`helix-cli/src/commands/compile.rs:110-118`). The container then `cargo build`s the resulting crate; runtime handler registration happens through the `inventory` crate (`helix-container/src/main.rs:113-145`) — proc-macros emit `inventory::submit!` calls and the binary harvests them at startup.

### Pattern (clean-room description)

> A typed graph DSL is parsed (pest), analyzed against a versioned schema with insertion-ordered field tables, and lowered to native Rust handler functions that are statically compiled into the server binary. Mutating queries are tagged at proc-macro time; the runtime gateway uses that tag to route to a single-writer channel. Embedding/network IO is hoisted out of the transaction. Handler registration is automatic via a compile-time inventory pattern (no runtime registration step).

The deep, novel idea is: **the DSL is closed, statically typed, and compiled.** There is no `eval(sql)` surface. Every query is a known endpoint, every parameter has a Rust type, every return shape is a Rust struct. The DB cannot be made to execute an unplanned operation — the attack surface that exists in Cypher/SQL servers is gone by construction.

## A.3 Comparison with COS

| Concern | HelixDB | luum-agent-os (Engram) |
|---|---|---|
| Storage substrate | LMDB via `heed3` (mmap, MVCC, ACID) | SQLite (file-based, single-writer, WAL) — `lib/engram_client.py` and HTTP variant at `lib/engram_http_client.py`. |
| Schema model | Nodes / Edges / Vectors as primary types | Observations + relations + topic-keys (graph implicit, not first-class). |
| Query surface | Compiled HelixQL → Rust handlers (no string queries) | Python API (`mem_save`, `mem_search`, `mem_get_observation`, …) over MCP/HTTP. **No DSL, no compiler.** |
| Type safety of queries | Static: schema-checked at compile time | Dynamic: arguments validated at MCP call. |
| Concurrent writers | Application-level single-writer channel + N reader workers (`helix_gateway/worker_pool/mod.rs`) | SQLite WAL handles it; not orchestrated at app layer. |
| Migrations | Versioned `Rule::migration_def` per schema version, with proc-macro-registered transition functions (`helix-container/src/main.rs:63-98`) | Engram has schema-evolution work in `lib/engram_wave2_schema.py`; not DSL-driven. |
| Embedding call placement | Hoisted out of transaction (`generator/queries.rs:75-100`) | N/A — embeddings external, not part of a transaction. |

### What COS could borrow (deferred to Annex E)

- The **compile-DSL contract** (Primitive #1) — only applicable if Engram ever grows beyond ad-hoc Python calls toward a typed agent-facing API surface.
- The **hoisted-embedding pattern** — directly applicable to any future Engram crystallizer pipeline.
- The **secondary-index-from-schema-flag** pattern (`analyzer/mod.rs:75-82`) — useful if Engram migrates to a richer schema layer.

### What is *not* applicable

- LMDB swap-in. SQLite already wins on operational simplicity at Engram's scale (sessions × project, not high-throughput OLTP). No code-path benefit justifies the mmap/ACID-substrate cost.
- HelixQL itself. Engram's surface is Python+MCP; adding a DSL would *increase* attack surface, not reduce it.

## A.4 Clean-room constraint

Anyone reimplementing the patterns above must:
1. Not read `helix-db/src/helixc/generator/queries.rs` while writing the COS emitter.
2. Re-derive the IR from the documented HelixQL grammar (or a re-specified COS grammar), not from the parser source.
3. Use a different identifier set, different file layout, and different error model.
4. Record the chain of design decisions in an ADR under `docs/04-Concepts/architecture/adr/`, including the explicit statement that no AGPL source was copied.
