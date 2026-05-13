---
adr: 290
title: 'Five Agent Quality-of-Life Patterns: Lazy Imports, Typed Hook Events, MCP Sync↔Async Bridge, Memory Quality Scoring, Reflection Loop'
status: accepted
implementation_status: implemented
date: '2026-05-13'
supersedes: []
superseded_by: null
implementation_files:
  - lib/lazy_imports.py
  - lib/hook_event_types.py
  - lib/mcp_thread_bridge.py
  - lib/engram_wave3_schema.py
  - lib/agent_reflection.py
tier: maintainer
tags:
  - agents
  - reliability
  - memory
  - reflection
  - performance
classification_basis: five independent agent-runtime patterns implemented as reusable modules with unit tests; quality scoring extends ADR-287 schema additively
verification:
  level: strong
  commands:
    - python3 -m pytest tests/unit/test_lazy_imports.py tests/unit/test_hook_event_types.py tests/unit/test_mcp_thread_bridge.py tests/unit/test_engram_quality_scoring.py tests/unit/test_agent_reflection.py -q
  proves:
    - lazy_import_thread_safe_single_factory_call
    - hook_event_payload_parses_to_typed_dataclass
    - mcp_thread_bridge_propagates_results_and_exceptions
    - quality_score_weights_and_filter_deterministic
    - reflection_loop_respects_min_and_max
---

# ADR-290 — Five Agent Quality-of-Life Patterns

## Status

Accepted

**Date:** 2026-05-13
**Owner:** orchestrator
**Tier:** maintainer
**Authors:** orchestrator
**Related:** ADR-287 (engram v3 schema — Pattern 4 extends it), ADR-289 (three-layer knowledge architecture), ADR-285 (skill registry drift), ADR-286 (stack-aware skill recommendation)

---

## Context

Five small but recurring quality gaps were observed across the agent runtime, memory subsystem, hook layer, and MCP transport. Each gap is independent of the others, none of them require touching load-bearing modules (`skill_router.py`, `dispatch.py`), and each can be closed by a single reusable module plus unit tests.

The five gaps:

1. **Startup latency from eager imports.** Several `lib/*.py` modules import `yaml`, `rich`, `litellm`, or `openai` at module load time. These imports are paid by every short-lived process — including hook bodies that never reach the code path that needs them. There is no shared, thread-safe deferred-import primitive in the codebase, so the obvious workaround (inline imports) ends up duplicated and inconsistent.
2. **Hook payloads are untyped dicts.** 237 hook scripts parse JSON event payloads as ad-hoc dicts with manual key fishing (`payload.get("tool_name")`). There is no central schema describing what fields each hook event carries, no static guarantee that a misspelled field name surfaces at parse time, and no roundtrip contract.
3. **MCP transport sometimes needs sync↔async bridging.** The MCP daemon protocol is async-native. Several internal callers (hooks, CLI scripts, batch tools) are synchronous and need to invoke an async coroutine without bringing up their own event loop on every call. Reusing the parent thread's event loop is unsafe; spawning a fresh loop per call is wasteful and loses connection state.
4. **Engram observations have no machine-quality signal.** ADR-287 added evidence linkage, but every claim is still treated as equally retrievable. There is no way for a writer to attach a structured quality estimate (completeness, relevance, clarity, accuracy) and no way for a reader to filter low-quality claims out of a search.
5. **No reflection loop.** Today an agent produces one response per call. There is no built-in iterative critique step where the agent (or a separate critic) inspects a draft response and decides whether another pass is warranted. This is a feature gain, not a bug fix: luum-cognitive-os currently has no reflection primitive at all.

---

## Decision

Adopt five small, independent patterns. Each is delivered as one module plus one focused test file.

### Pattern 1 — Lazy import primitive (`lib/lazy_imports.py`)

**Problem.** Several modules pay import cost for heavy dependencies they need on at most one code path. The naive fix — inline the import inside the function — duplicates the deferred-load logic, hides whether the module has been resolved, and is not thread-safe under concurrent first use.

**Solution.** A single `LazyImport(factory)` class that resolves the wrapped object exactly once, lazily, under double-checked locking. The class exposes a `loaded: bool` property so callers can introspect state without forcing a load. Two existing sites (`lib/adapter_compile.py`, `lib/cross_stack_license_audit.py`) are converted as proof-of-concept; the rest of the codebase can adopt the primitive incrementally.

**Test approach.** Concurrent first access from ten threads gated by a `threading.Barrier`, asserting the factory was invoked exactly once. Independence between instances. `loaded` transition from `False` → `True` after first access.

**Measured impact.** Import cost of the heavy dependency is shifted from module-load time to first use. For `yaml` (≈4ms cold load on the reference machine) this is below the noise floor of a single hook execution, but the cumulative savings across 237 hook invocations per session compound. The primitive does not regress hot-path performance — once loaded, every subsequent `.get()` is an attribute access behind a fast `loaded`-check.

### Pattern 2 — Typed hook event registry (`lib/hook_event_types.py`)

**Problem.** Hook payload dicts are silently lossy. A typo like `tool_inpiut` returns `None` from `.get()` and the hook proceeds with broken behavior. There is no single place to look up "what fields can a `PreToolUse` payload carry?".

**Solution.** A frozen dataclass per Claude Code hook event (`SessionStartEvent`, `PreToolUseEvent`, `PostToolUseEvent`, `StopEvent`, `SubagentStartEvent`) plus a single `parse_event(payload: dict) -> HookEvent` dispatcher that routes by `hook_event_name`. Unknown event names and missing required fields raise a clear `HookPayloadError` at parse time, not at field-access time.

**Solution shape, not a migration.** Existing hooks are not rewritten in this ADR. The module is the canonical schema; future hooks adopt the dataclasses opportunistically and old hooks can be migrated one at a time without coupling to this ADR.

**Test approach.** Round-trip parse-then-inspect for each event type. Missing-field payload raises `HookPayloadError` with the field name surfaced. Unknown `hook_event_name` raises a clear error.

### Pattern 3 — MCP sync↔async thread bridge (`lib/mcp_thread_bridge.py`)

**Problem.** A synchronous caller cannot safely `asyncio.run(coro)` if it might be inside another event loop, and creating a fresh loop per call is wasteful and forgets state.

**Solution.** `MCPThreadBridge` owns one dedicated worker thread running a single private `asyncio` event loop. `bridge.call(coro, timeout=30)` enqueues the coroutine via `asyncio.run_coroutine_threadsafe`, blocks the calling thread on the resulting `concurrent.futures.Future`, and either returns the coroutine's value, re-raises its exception, or raises `TimeoutError`. `close()` stops the loop and joins the worker. The class is a regular context manager.

**Test approach.** Coroutine returns a value → bridge returns it. Coroutine raises → bridge re-raises the same exception type. Coroutine sleeps longer than `timeout` → `TimeoutError`. `close()` joins the worker thread within a small bound. Tests define coroutines inline; no real MCP server is required.

### Pattern 4 — Memory quality scoring (extends ADR-287 schema)

**Problem.** Engram v3 (ADR-287) added evidence sources but every claim is still treated as equally retrievable. A reader has no way to express "give me only high-quality claims".

**Solution.** Additive extension of the v3 `Claim` dataclass in `lib/engram_wave3_schema.py` with four optional `float | None` fields scored on `[0, 1]`: `quality_completeness`, `quality_relevance`, `quality_clarity`, `quality_accuracy`. A pure function `compute_quality_score(completeness, relevance, clarity, accuracy, weights=None) -> float` returns the weighted mean (uniform 0.25 default weights). A `min_quality` parameter is added to `search_bm25` in `lib/engram_fts5_search.py`. Filtering policy: **claims with any missing quality field are treated as quality 0** and filtered out when `min_quality > 0`. When `min_quality is None` (default), filtering is disabled and all existing claims continue to surface, preserving backwards compatibility.

**Test approach.** `compute_quality_score` is deterministic with custom weights and clamps inputs to `[0, 1]`. `search_bm25` with `min_quality=None` returns the same result set as before (regression guard). `search_bm25` with `min_quality > 0` excludes rows where any of the four quality columns is `NULL`. Rows with all four columns scored above the threshold pass.

**Measured impact.** Reader-driven filter; zero write-side cost when scores are not supplied. Score columns are nullable, so the migration is additive and ADR-287 callers do not need to change.

### Pattern 5 — Agent reflection loop (`lib/agent_reflection.py`) — feature gain

**Problem.** No reflection primitive exists in luum-cognitive-os today. Agents produce one response per call with no built-in critique step.

**Solution.** `AgentReflector(config: ReflectionConfig)` runs an iterative reflection loop. `config.llm_call: Callable[[str], tuple[str, Literal["yes","no"]]]` returns a reflection string and a satisfaction verdict. The loop is bounded by `min_reflect` (≥1) and `max_reflect`. It exits early on `"yes"` once `min_reflect` is reached. It exits unconditionally at `max_reflect`. `llm_call=None` raises `ValueError` at construction time. The method `reflect(response: str) -> list[ReflectionResult]` returns the full trajectory: every iteration with its reflection text, the verdict, and the 1-indexed iteration number.

**Out of scope for this ADR.** Wiring the reflector into `agent_runner` is intentionally deferred. The module is a leaf that can be composed into any caller without coupling.

**Test approach.** `"yes"` on iteration 1 with `min_reflect=1` exits after one iteration. `"no"`, `"no"`, `"yes"` exits after three iterations when `min_reflect=1`. `max_reflect=2` with always-`"no"` stops at two iterations. `min_reflect=2` with `"yes"` on iteration 1 continues through iteration 2 because the floor has not been reached.

---

## Consequences

### Positive

- Five independent improvements landed without touching `skill_router.py`, `dispatch.py`, or the other ADR-287 modules.
- Each pattern is a leaf module with no cross-imports between them; any one can be reverted without affecting the others.
- Pattern 4 strictly extends ADR-287; existing engram callers continue to work because every new field defaults to `None` and the `min_quality` filter defaults to `None` (disabled).
- Pattern 5 is the first reflection primitive in the codebase. Future agent wrappers can opt in without rewriting their call sites.
- All five modules ship with focused unit tests that exercise real behavior (concurrent threading, exception propagation, schema migration on a temp DB, etc.).

### Negative

- Five new modules to maintain. Each is small (well under 200 LOC) and self-contained.
- Pattern 2 does not migrate the existing 237 hooks; this is intentional but defers the actual win until hooks opt in one by one.
- Pattern 4's "missing == 0" filter policy is conservative. A writer who supplies three of four quality fields and forgets the fourth will be filtered out at any `min_quality > 0`. Documented in the function docstring.

### Risks

- Pattern 3 holds a long-lived worker thread for the lifetime of the bridge. Callers that forget to `close()` will leak a thread. Tests cover the close path.
- Pattern 5 calls into an opaque `llm_call`. If `llm_call` itself raises, the exception propagates and the trajectory list is lost. By design — the caller decides retry policy.

---

## Migration

All five patterns are opt-in and additive.

- **Pattern 1:** New code can `from lib.lazy_imports import LazyImport` immediately. Two existing sites are converted as the reference implementation.
- **Pattern 2:** Existing hooks continue to parse dicts manually. New hooks may import `parse_event` to obtain a typed event object. A future ADR may sweep the 237 existing hooks.
- **Pattern 3:** Callers that today juggle an event loop manually can replace that code with one `MCPThreadBridge` per long-lived process.
- **Pattern 4:** Writers may supply quality scores via the existing engram write path (the schema columns are nullable). Readers may pass `min_quality` to `search_bm25` to filter; the default is no filtering.
- **Pattern 5:** Any caller that wants iterative reflection composes `AgentReflector` around its existing LLM call.

---

## Related ADRs

- **ADR-287** — Engram v3 evidence-grounded claims. Pattern 4 extends `lib/engram_wave3_schema.py` and `lib/engram_fts5_search.py` from this ADR.
- **ADR-289** — Three-layer knowledge architecture.
- **ADR-285 / ADR-286** — Skill registry and stack-aware recommendation context.

## Alternatives rejected

1. **Rewrite all existing hooks to typed events in one sweep.** Rejected because
   the hook surface is large and stateful; the safer migration is to provide the
   canonical parser now and adopt it opportunistically as hooks are touched.
2. **Use `asyncio.run()` directly for MCP calls.** Rejected because synchronous
   callers may already be inside an event loop and because per-call loop startup
   loses transport state.
3. **Wire reflection directly into `agent_runner` immediately.** Rejected
   because this ADR establishes a leaf primitive; runtime policy for when to
   reflect belongs in a follow-up integration decision.

## Verification

```bash
python3 -m pytest tests/unit/test_lazy_imports.py tests/unit/test_hook_event_types.py tests/unit/test_mcp_thread_bridge.py tests/unit/test_engram_quality_scoring.py tests/unit/test_agent_reflection.py -q
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

These checks prove the lazy import primitive is thread-safe, hook payloads parse
into typed dataclasses, the MCP bridge returns/cancels work correctly, Engram
quality scoring/filtering is deterministic, the reflection loop honors min/max
bounds, and the ADR satisfies the post-ADR-067 documentation contract.
