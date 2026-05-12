---
adr: 33
title: Harness-agnostic event capture layer
status: accepted
implementation_status: partial
date: '2026-04-20'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit pending/deferred/planned scope
partial_remaining: The Executor will become a capture source via its own adapter entry (future work).
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-033 — Harness-agnostic event capture layer

**Status**: Accepted
**Date**: 2026-04-20
**Related**: ADR-028b (SLO 9 agent heartbeats), ADR-032 (orchestrator trap awareness), D43 (advisory-llm packages extraction)

## Context

The Cognitive OS observes agent activity through two JSONL streams:

- `.cognitive-os/metrics/agent-heartbeat.jsonl` — consumed by SLO 9 watchdog and `AgentBusMetrics`.
- `.cognitive-os/metrics/cost-events.jsonl` — token/cost accounting.

Today, **every capture path is coupled to Claude Code's lifecycle**. Concretely:

1. `hooks/native-agent-heartbeat.sh` is a `PreToolUse:Agent` / `PostToolUse:Agent` hook. It relies on Claude Code's stdin JSON contract (`tool_name`, `tool_use_id`, `tool_input`, `tool_response`) and on CC's hook registration model.
2. `ClaudeExecutor` provides richer telemetry, but it too is a Claude-specific wrapper (`anthropic` SDK + `task-notification` schema).
3. There is **no** intermediate "canonical event" vocabulary. Each consumer re-parses harness-specific shapes.

The codebase already hints at harness abstraction intent: `ORCHESTRATOR_MODE=executor|fire_and_forget` in `lib/orchestrator_mode.py`, the session banner, and the README's multi-harness roadmap. But only Claude Code is wired. Running the same rules under **OpenCode**, **Aider**, **Cursor**, or **Continue** produces zero events — the storage is portable (JSONL), the capture is not.

Motivation:
- **Portability**: we want the same telemetry regardless of which IDE/CLI a contributor uses.
- **Separation of concerns**: SLO dashboards, cost reports, and the error-learning pipeline should read a stable schema; they should not carry harness-specific parsing logic.
- **Future-proofing**: a new harness (or a new CC hook schema version) should be an additive change, not a rewrite.

## Decision

Introduce a **`HarnessAdapter`** abstraction under `lib/harness_adapter/`:

- A thin **ABC** defining three operations: `detect_harness`, `parse_event`, `emit_canonical`.
- A **canonical event schema** (`AgentStart`, `AgentEnd`, `ToolUse`, `TokenUsage`, `HeartbeatTick`) that every adapter MUST translate to.
- A **dispatch** module (`dispatch.handle_event`) that shell hooks, watchers, and library code call with the raw payload. Dispatch detects the harness, picks the adapter, parses, and emits.
- A **Claude Code adapter** (`claude_code.py`) that is the reference implementation; it also preserves the legacy side-effects (`agent-heartbeat.jsonl` MetricEvent write, `.cognitive-os/agent-bus/<agent>/heartbeat.jsonl` FallbackBus write) so existing consumers keep working byte-compatibly.
- A **POC adapter for Aider** (`aider.py`) as passive file-watcher proof-of-concept — it parses `.aider.chat.history.md` deltas and emits canonical events.

Hook files (`hooks/native-agent-heartbeat.sh`) become thin shims that forward stdin to `dispatch.handle_event`. Hook registration is unchanged.

## Canonical event schema

All events share `{event_type: string, agent_id: string, session_id?: string}` and carry event-specific fields below. JSON Schema fragments (informative):

```json
// AgentStart
{
  "event_type": "agent_start",
  "agent_id":   "string",
  "started_at": "number (unix epoch seconds)",
  "tool_name":  "string",
  "model":      "string | null",
  "cwd":        "string | null",
  "parent_id":  "string | null",
  "input_summary": "string | null"
}

// AgentEnd
{
  "event_type": "agent_end",
  "agent_id":   "string",
  "ended_at":   "number",
  "exit_status":"success | error | timeout | unknown",
  "duration_ms":"integer | null",
  "token_usage": { "input": "int", "output": "int", "cached": "int" },
  "cost_usd":   "number | null"
}

// ToolUse
{
  "event_type":   "tool_use",
  "agent_id":     "string",
  "tool_name":    "string",
  "started_at":   "number",
  "duration_ms":  "integer | null",
  "exit_status":  "string",
  "tool_input_hash": "string | null"
}

// TokenUsage
{
  "event_type":     "token_usage",
  "agent_id":       "string",
  "ts":             "number",
  "input_tokens":   "integer",
  "output_tokens":  "integer",
  "cache_read":     "integer | null",
  "cache_creation": "integer | null",
  "model":          "string | null"
}

// HeartbeatTick
{
  "event_type":        "heartbeat_tick",
  "agent_id":          "string",
  "ts":                "number",
  "alive":             "boolean",
  "tool_call_count":   "integer | null",
  "remaining_budget":  "number | null"
}
```

Reference Python definitions live in `lib/harness_adapter/base.py` (dataclasses with stable `to_dict` / `from_dict` roundtrip).

## Adapter API

```python
class HarnessAdapter(ABC):
    name: ClassVar[HarnessName]
    default_output: ClassVar[str] = ".cognitive-os/metrics/canonical-events.jsonl"

    @classmethod
    @abstractmethod
    def detect_harness(cls, raw: Any) -> Optional[HarnessName]: ...

    @abstractmethod
    def parse_event(self, raw: dict) -> list[CanonicalEvent]: ...

    def emit_canonical(self, event: CanonicalEvent, output_path: Path | None = None) -> Path:
        # Appends event.to_json() to JSONL. Base-class implementation is fine
        # for most adapters; override only if destination depends on event type.
```

Dispatch flow (`lib.harness_adapter.dispatch.handle_event`):

1. Decode raw string/bytes → dict.
2. Iterate `ADAPTERS` (ordered, most specific first), pick first where `detect_harness` returns non-None.
3. Call `parse_event` → list[CanonicalEvent].
4. For each event: `emit_canonical` to the adapter's default stream.
5. Claude Code-specific backwards-compat side-effects (FallbackBus + AgentBusMetrics) run only when the CC adapter emits a `HeartbeatTick`.

## Consequences

**Positive**:
- **Portability**: adding OpenCode/Cursor/Continue means one new file in `lib/harness_adapter/` + one line in `dispatch.ADAPTERS`. No touch to SLO, cost, or rule logic.
- **Testability**: canonical events are pure dataclasses; adapters are unit-testable without running a harness. The ABC enforces the contract at import time.
- **Evolvability**: canonical schema is versioned by `event_type` values. Adding fields is additive (dataclass default factories). Removing/renaming requires a minor bump and migration note — deliberate.
- **No regression**: existing `agent-heartbeat.jsonl` readers see the same MetricEvents (the CC adapter fires them via the legacy path). Integration test `tests/integration/test_native_agent_heartbeat.py` continues to pass (4/4).

**Negative**:
- **Adapter maintenance burden**: each harness requires ongoing care when its payload schema drifts. Mitigated by the ABC contract (parse failures degrade gracefully to empty event list) and by per-adapter unit tests.
- **Schema evolution risk**: downstream readers now depend on the canonical schema. Changes must go through ADR amendments and a deprecation window. We accept this cost as the price of the harness-independence property.
- **Two-stream period**: during transition, both `agent-heartbeat.jsonl` (legacy) and `canonical-events.jsonl` (new) are written. ~20 bytes/event extra disk; bounded by the existing log rotation policy (SLO 7, <1 MiB/session).

**Neutral**:
- `ORCHESTRATOR_MODE=executor` remains valuable for **prompt-side** mid-flight injection (ADR-032 territory) — orthogonal to capture. The Executor will become a capture source via its own adapter entry (future work).

## Alternatives considered

### A. Passive stdout parsing
Scrape every harness's stdout and regex-match for tool-use / agent-launch patterns.

**Rejected**: brittle (each harness changes output format freely), lossy (no tool_use_id, no token accounting), and slow. Canonical events would still be the target shape — we'd just be writing worse adapters.

### B. One hook per harness, each writing straight to `agent-heartbeat.jsonl`
Duplicate the existing CC hook for each harness, inline the schema mapping.

**Rejected**: copy-paste spaghetti. Schema changes multiply by N harnesses. No canonical layer means consumers must still know every harness's quirks.

### C. Status quo — accept Claude Code lock-in
Do nothing. Defer portability until a concrete second-harness requirement lands.

**Rejected**: we already have **two** partial capture mechanisms in the tree (native-agent-heartbeat.sh + ClaudeExecutor) and no schema convergence between them. The debt is real today; this ADR pays it down with proportional scope (base + CC + one POC adapter).

## Rollout plan

Phased rollout (`v0.13.x` → `v0.15.0`):

1. **v0.13** (this ADR) — ship `lib/harness_adapter/` + CC adapter + Aider POC. `native-agent-heartbeat.sh` refactored to thin shim. Both legacy and canonical streams written.
2. **v0.14** — migrate `cost-events.jsonl` capture to use the same adapter layer (extract token-accounting logic from hook chain into the CC adapter). Downstream readers begin consuming canonical events; legacy stream continues in parallel.
3. **v0.15.0** — deprecate legacy `agent-heartbeat.jsonl` in favor of `canonical-events.jsonl`. Provide a read-side shim (`lib/legacy_event_reader.py`) for any out-of-tree consumer. Remove legacy side-effects from the CC adapter after one release.

**Migration guarantee**: at no point is there a gap. Until v0.15.0, the CC adapter writes both streams. Consumers that upgrade to canonical events can do so at their own pace.

## Migration notes

- **Hook authors**: nothing to do. `hooks/native-agent-heartbeat.sh` still exists and does its job; it just delegates to `dispatch.handle_event` internally.
- **Consumer authors**: prefer `canonical-events.jsonl` for new code. Read through `CanonicalEvent.from_dict` for forward-compatibility.
- **Harness authors**: see `docs/05-Methodology/guides/adding-a-harness-adapter.md`.
- **Test authors**: tests that stub stdin payloads for the CC hook continue to work unchanged.

## Acceptance summary

- `from lib.harness_adapter.base import HarnessAdapter, CanonicalEvent` — OK
- `ClaudeCodeAdapter().name` → `HarnessName.CLAUDE_CODE` — OK
- `AiderAdapter` importable — OK
- `hooks/native-agent-heartbeat.sh` refactored — grep confirms `harness_adapter.dispatch`
- `tests/unit/test_harness_adapter_*.py` + `tests/integration/test_harness_adapter_dispatch.py` — 14/14 pass
- `tests/integration/test_native_agent_heartbeat.py` — 4/4 pass (no regression)
