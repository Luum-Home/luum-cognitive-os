---
title: "HelixDB Annex C — Runtime gateway, worker pool, and MCP surface"
date: 2026-05-11
parent: helixdb-comparison-2026-05-11.md
scope: research-only
license_constraint: "AGPL-3.0 — pattern-only adoption, clean-room rewrite required. No code, identifiers, comments or test fixtures may be reused."
---

# Annex C — Runtime gateway, worker pool, and MCP surface

## C.1 Gateway boot path (`helix-container/src/main.rs`)

The deployable binary is 159 lines. The interesting bits:

1. **Env-driven configuration only.** `HELIX_DATA_DIR` (`:42-48`), `HELIX_PORT` (default 6969; `:51-56`), `HELIX_API_KEY` (read inside `helix_gateway/key_verification.rs:7-22`), `HELIX_CLUSTER_ID` (`gateway.rs:56`), `HELIX_CORES_OVERRIDE` (`gateway.rs:72-89`). No config file in the runtime path; the only config-file work happens at compile time on the CLI side.
2. **Inventory-pattern route registration.** Each `#[handler]`-annotated function (emitted by the codegen described in Annex A) calls `inventory::submit!(HandlerSubmission(…))` at static-init time. The container collects them at `:113-145` and builds two maps: a `HashMap<String, HandlerFn>` for routes and a `HashSet<String>` for the writes subset. MCP routes are collected the same way at `:136-144`.
3. **Migration transition collection.** Schema version transitions are also inventory-registered (`:63-98`) and are validated at startup with three assertions: `from < to`, both > 0, and `to - from == 1` (single-step transitions only — multi-step migrations are composed from single-step links, not declared directly).
4. **The whole boot path is synchronous.** No `#[tokio::main]` on the container; tokio is spawned later inside `HelixGateway::run` (`helix-db/src/helix_gateway/gateway.rs:67-…`).

### Pattern (clean-room description)

> Handler registration is compile-time-static via a linker-collected inventory; the binary never executes a "registerRoute" function. Mutating handlers are tagged at the macro layer and propagated to a single-writer dispatch channel. Migrations are decomposed to single-version steps and validated at startup before the network listener opens.

## C.2 Worker pool (`helix-db/src/helix_gateway/worker_pool/mod.rs`)

`WorkerPool` (`:21-27`) holds:
- `tx: Sender<ReqMsg>` — read-channel.
- `write_tx: Sender<ReqMsg>` — write-channel.
- `_workers: Vec<Worker>` — N reader workers, core-pinned.
- `_writer_worker: Worker` — exactly one writer.

Construction (`:30-81`):
- `flume::bounded::<ReqMsg>(1000)` for both channels — backpressure at 1000 in-flight requests.
- `num_workers` must be `≥ 2` and `% 2 == 0` (`:42-49`). The `i % 2 == 0` flag on `Worker::start` (`:61`) tells half the workers to act as a "parity select" — see comment "for parity to act as a select". This is a niche pattern to ensure fairness across two task sources without `tokio::select!`.
- The dedicated writer (`:67-72`) is not core-pinned (single thread).

Dispatch (`:85-100`):
- A `oneshot::channel` for the response is created per request.
- `router.is_write_route(req.name)` decides write vs read channel.
- On channel close, returns `HelixError::Graph(GraphError::New("Server is shutting down"))` — clean shutdown semantics.

### Pattern (clean-room description)

> A single-writer / N-reader worker pool with bounded channels and per-request oneshot reply channels. The decision to route to the writer is computed from a `HashSet<String>` of mutating-route names populated at startup. Backpressure is explicit (bounded channel, not unbounded).

## C.3 Router and request types (`helix-db/src/helix_gateway/router/router.rs`)

- `HandlerInput { request, graph: Arc<HelixGraphEngine> }` (`:18-22`) — every handler gets the full graph engine handle.
- `BasicHandlerFn = fn(HandlerInput) -> Result<Response, GraphError>` (`:48`) — plain function pointers; cheap to call.
- `HandlerFn = Arc<dyn Fn(…) + Send + Sync>` (`:51`) — wrapped for the cross-thread map.
- `HandlerSubmission(Handler { name, func, is_write })` (`:56-66`) — collected by `inventory::collect!(HandlerSubmission)` at `:73`.

The most interesting design choice: **`IoContFn`** (`:31-46`). An error variant `GraphError::IoNeeded(IoContFn)` lets a handler *suspend* the LMDB transaction, return control to a tokio executor that performs IO (typically an embedding call), then resume by sending a closure back over a `flume::Sender<ContMsg>`. This is the runtime counterpart of the "hoist embedding calls" generator pattern (Annex A §A.2). Concretely:

- `ContMsg = (RetChan, Box<dyn FnOnce() -> Result<Response, GraphError>>)` (`:24-28`).
- `IoContFn(Box<dyn FnOnce(ContChan, RetChan) -> ContFut>)` — wraps a future the executor drives.
- The pattern lets the synchronous LMDB transaction be split around an `await` point **without** holding the LMDB write-lock during IO.

### Pattern (clean-room description)

> Long-running IO is expressed by *returning* a continuation from inside the synchronous transaction handler. The executor receives the continuation, awaits the IO on a separate tokio runtime, then schedules the closure to run inside a *new* transaction. The original LMDB lock is released across the await — no transaction holds the writer slot longer than its CPU work needs.

## C.4 MCP surface

There are two distinct MCP-related layers, easy to conflate:

### Layer 1 — MCP server itself (`helix-db/src/helix_gateway/mcp/mcp.rs`)

`McpConnections` (`:24-63`) holds a `HashMap<connection_id, MCPConnection>`. Each connection carries a *query chain* — an ordered `Vec<QueryStep>` (alias of `ToolArgs`, `:22`) plus a current position. Stateful: connections accumulate steps and walk them.

`McpBackend` (`:65-73`) wraps `Arc<HelixGraphStorage>` directly — MCP tools touch storage without going through the compiled-query layer. This is a noteworthy difference from the regular HTTP handler path.

### Layer 2 — Tool schema (`helix-db/src/helix_gateway/mcp/tools.rs:31-83`)

The MCP tool surface is a **strongly-typed enum** with `#[serde(tag = "tool_name", content = "args")]`:

```
ToolArgs::{
    OutStep      { edge_label, edge_type: Node|Vec, filter: Option<FilterTraversal> },
    OutEStep     { edge_label, filter },
    InStep       { … },
    InEStep      { … },
    NFromType    { node_type },
    EFromType    { edge_type },
    FilterItems  { filter },
    OrderBy      { properties, order: Asc|Desc },
    SearchKeyword{ query, limit, label },     // BM25
    SearchVecText{ query, label, k },         // embed → HNSW
    SearchVec    { vector, k, min_score, cutoff },  // raw HNSW
}
```

`FilterTraversal` (`:101-105`) is recursive — filters can themselves contain `Vec<ToolArgs>` to express predicate sub-traversals. `Operator` (`:107-…`) is the obvious `Eq | Neq | Gt | Lt | Gte | Lte` set; values come from the protocol-level `Value` type.

### What this means in practice

The MCP client (an LLM agent) does **not** issue natural-language or string queries. It composes a typed traversal chain. The server validates the chain via Rust's `serde` + the enum's exhaustiveness — invalid combinations cannot be expressed. This is the same defence-in-depth argument as the compiled-DSL pattern, applied to the MCP surface: no `eval`, no string parser at runtime, no SQL injection class.

### Pattern (clean-room description)

> The MCP tool catalogue is a closed, recursive ADT of traversal primitives (out/in/source/filter/order/search) parameterized by literal labels and values. Agents compose chains; the server validates by type. The MCP layer connects directly to the storage layer, bypassing the compiled-query path, so MCP can expose primitives that no compiled query exposes (and vice versa).

## C.5 Auth

`helix-db/src/helix_gateway/key_verification.rs`:
- `HELIX_API_KEY` env var, expected to be a hex-encoded SHA-256 hash (`:13-22`) — clients send the *preimage*, server hashes and compares.
- `subtle::ConstantTimeEq` (`:31`) — proper constant-time comparison.
- The whole module is `#[inline(always)]` and feature-gated by `api-key` (`Cargo.toml:80 api-key = []`); the default build does **not** enable it. The `production` cargo feature does (`Cargo.toml:87 production = ["api-key","server"]`).

Verdict: textbook correct on the constant-time front, but auth-disabled-by-default in the default profile. Annex D treats the supply-chain implications.

## C.6 Comparison with COS

| Concern | HelixDB | luum-agent-os |
|---|---|---|
| HTTP gateway | axum 0.8 inside `HelixGateway::run` | `lib/engram_http_client.py` — client side only; Engram server lives in the `engram` plugin. |
| Worker pool | core-pinned N readers + 1 writer, flume bounded channels | Python GIL + SQLite WAL; no explicit pool. |
| Route registration | compile-time inventory | dynamic — MCP tools enumerated by import. |
| Auth | hex-SHA256 preimage check, constant-time, feature-gated | Engram MCP uses Claude Code's transport; no separate API-key layer. |
| MCP tool surface | typed ADT (`ToolArgs` enum, 11 variants) | typed but Python-side (`mem_save`, `mem_search`, …); not a recursive ADT. |
| Multi-tenant scoping | `HELIX_CLUSTER_ID` env var passed through `HelixGateway` | Engram project/scope param on each tool call. |
| IO-during-txn pattern | `IoContFn` continuation (txn split around await) | Not applicable — Engram does not have long transactions. |

### What COS could borrow (deferred to Annex E)

- **Typed-ADT MCP surface** (Primitive #2). The `ToolArgs` enum is the model we'd want if/when Engram or another COS subsystem grows a richer MCP tool catalogue. Right now Engram tools are flat verbs; HelixDB's recursive composability is more powerful at the cost of a small grammar.
- **Single-writer + N-reader worker pool** — only useful if/when a COS component starts hosting concurrent agents against a shared mutable backend.
- **Continuation-style IO-during-transaction** — useful template for any future Engram crystallizer that wants to call an LLM inside a logical transaction.

### What is *not* applicable

- Core-pinning. Python orchestrator is not CPU-bound at the level where pinning helps.
- `flume::bounded(1000)`. Our backpressure points are at the agent-launch layer (rate-limit & queue-drain hooks), not at HTTP layer.
- An axum HTTP gateway. Adding one would be net-negative complexity.

## C.7 Clean-room constraint

- Do not transcribe enum variant names, tag/content schema strings, env-var names, or default port values (`6969`).
- Re-derive the IO-continuation pattern from the *requirement* ("release LMDB write-lock across embedding call") not from `IoContFn`.
- If the typed-ADT MCP pattern is adopted, choose new variant names aligned with COS memory verbs (e.g. `Recall`, `Crystallize`, `Project`), not HelixDB's graph-traversal verbs.
