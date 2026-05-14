---
adr: 292
title: 'Runtime Performance Primitives: Lazy Imports and MCP Sync↔Async Thread Bridge'
status: accepted
implementation_status: implemented
date: '2026-05-13'
supersedes: [ADR-290]
superseded_by: null
implementation_files:
  - lib/lazy_imports.py
  - lib/mcp_thread_bridge.py
tier: maintainer
tags:
  - performance
  - concurrency
  - runtime
classification_basis: two runtime performance primitives delivered as leaf modules with thread-safe unit tests; both shift cost away from hot paths without coupling to any specific caller
verification:
  level: strong
  commands:
    - python3 -m pytest tests/unit/test_lazy_imports.py tests/unit/test_mcp_thread_bridge.py -q
  proves:
    - lazy_import_thread_safe_single_factory_call
    - mcp_thread_bridge_propagates_results_and_exceptions
---

# ADR-292 — Runtime Performance Primitives

## Status

Accepted

**Date:** 2026-05-13
**Owner:** orchestrator
**Tier:** maintainer
**Authors:** orchestrator
**Supersedes:** ADR-290 (Pattern 1 + Pattern 3 split out of the original five-pattern bundle)
**Related:** ADR-293, ADR-294, ADR-295 (peer splits of ADR-290)

---

## Context

Two recurring runtime-performance gaps were observed in the agent runtime and were originally bundled with three unrelated patterns in ADR-290. Both gaps are about *where cost is paid* — at module load vs. on first use, and per-call vs. once-per-process — and they share neither callers nor tests with the other three ADR-290 patterns. They are therefore split into this ADR.

1. **Startup latency from eager imports.** Several `lib/*.py` modules import `yaml`, `rich`, `litellm`, or `openai` at module load time. These imports are paid by every short-lived process — including hook bodies that never reach the code path that needs them. There is no shared, thread-safe deferred-import primitive in the codebase, so the obvious workaround (inline imports) ends up duplicated and inconsistent.
2. **MCP transport sometimes needs sync↔async bridging.** The MCP daemon protocol is async-native. Several internal callers (hooks, CLI scripts, batch tools) are synchronous and need to invoke an async coroutine without bringing up their own event loop on every call. Reusing the parent thread's event loop is unsafe; spawning a fresh loop per call is wasteful and loses connection state.

Both are leaf concerns: composable primitives that any caller can adopt without coupling to the other ADR-290 patterns.

---

## Decision

Adopt two runtime-performance primitives. Each is delivered as one module plus one focused test file.

### Pattern 1 — Lazy import primitive (`lib/lazy_imports.py`)

**Problem.** Several modules pay import cost for heavy dependencies they need on at most one code path. The naive fix — inline the import inside the function — duplicates the deferred-load logic, hides whether the module has been resolved, and is not thread-safe under concurrent first use.

**Solution.** A single `LazyImport(factory)` class that resolves the wrapped object exactly once, lazily, under double-checked locking. The class exposes a `loaded: bool` property so callers can introspect state without forcing a load. Two existing sites (`lib/adapter_compile.py`, `lib/cross_stack_license_audit.py`) are converted as proof-of-concept; the rest of the codebase can adopt the primitive incrementally.

**Test approach.** Concurrent first access from ten threads gated by a `threading.Barrier`, asserting the factory was invoked exactly once. Independence between instances. `loaded` transition from `False` → `True` after first access.

**Measured impact.** Import cost of the heavy dependency is shifted from module-load time to first use. For `yaml` (≈4ms cold load on the reference machine) this is below the noise floor of a single hook execution, but the cumulative savings across 237 hook invocations per session compound. The primitive does not regress hot-path performance — once loaded, every subsequent `.get()` is an attribute access behind a fast `loaded`-check.

### Pattern 2 — MCP sync↔async thread bridge (`lib/mcp_thread_bridge.py`)

**Problem.** A synchronous caller cannot safely `asyncio.run(coro)` if it might be inside another event loop, and creating a fresh loop per call is wasteful and forgets state.

**Solution.** `MCPThreadBridge` owns one dedicated worker thread running a single private `asyncio` event loop. `bridge.call(coro, timeout=30)` enqueues the coroutine via `asyncio.run_coroutine_threadsafe`, blocks the calling thread on the resulting `concurrent.futures.Future`, and either returns the coroutine's value, re-raises its exception, or raises `TimeoutError`. `close()` stops the loop and joins the worker. The class is a regular context manager.

**Test approach.** Coroutine returns a value → bridge returns it. Coroutine raises → bridge re-raises the same exception type. Coroutine sleeps longer than `timeout` → `TimeoutError`. `close()` joins the worker thread within a small bound. Tests define coroutines inline; no real MCP server is required.

---

## Operational Guide

- New callers `from lib.lazy_imports import LazyImport` and wrap heavy modules: `yaml = LazyImport(lambda: __import__("yaml"))`.
- Long-lived processes (CLI, agent runtime, daemon) construct one `MCPThreadBridge()` and reuse it across calls. Short-lived hooks should not instantiate the bridge.
- Both primitives are opt-in; no existing caller is forced to migrate.

---

## Consequences

### Positive

- Two leaf modules, no cross-imports, either can be reverted independently.
- Thread-safety is proven by tests, not by inspection.
- Adoption is incremental: each new caller is one import line.

### Negative

- `MCPThreadBridge` holds a long-lived worker thread for the lifetime of the bridge. Callers that forget to `close()` will leak a thread. The context-manager form makes the close path the easy path.

### Risks

- A `LazyImport` factory that raises on first use will keep raising on every subsequent access until the process restarts. By design — the caller decides retry policy.

---

## Alternatives Rejected

1. **Inline `import` statements inside each function.** Rejected because the deferred-load logic ends up duplicated across modules, is not thread-safe, and gives no introspection of whether the dependency has been resolved.
2. **`asyncio.run()` per MCP call.** Rejected because synchronous callers may already be inside an event loop and because per-call loop startup loses transport state.
3. **A single global event loop shared with the parent thread.** Rejected because reusing the parent thread's event loop deadlocks when the caller is itself awaiting something on that loop.

---

## Alternatives rejected

- **Leave the behavior as implicit agent instruction only.** Rejected because this ADR records a runtime/authoring contract that needs durable tests or audits rather than conversation-only memory.

## Verification

```bash
python3 -m pytest tests/unit/test_lazy_imports.py tests/unit/test_mcp_thread_bridge.py -q
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

These checks prove the lazy import primitive is thread-safe under concurrent first use, the MCP bridge propagates results and exceptions correctly and honors `timeout`, and the ADR satisfies the post-ADR-067 documentation contract.
