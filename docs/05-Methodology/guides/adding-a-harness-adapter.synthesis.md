---
type: methodology-synthesis
source: docs/05-Methodology/guides/adding-a-harness-adapter.md
provenance: "Contributor recipe for wiring a new agent harness into COS telemetry via the ADR-033 canonical-event contract and the ADR-034 live-streaming extension."
---

## What it is
A how-to guide for contributors wiring a new agent harness (OpenCode, Cursor, Continue, a bespoke CLI, etc.) into Cognitive OS telemetry, covering both post-hoc event capture (ADR-033) and live streaming (ADR-034).

## Key mechanics
- **The contract:** an adapter translates a harness's native events into the canonical schema so downstream consumers (SLO watchdog, cost dashboard, error-learning) never see harness-specific shapes. Three methods to implement: `detect_harness(raw) -> HarnessName | None`, `parse_event(raw) -> list[CanonicalEvent]`, and optionally `emit_canonical` (default appends JSON lines to `.cognitive-os/metrics/canonical-events.jsonl`).
- **Five-step recipe:** (1) subclass `HarnessAdapter` in `packages/agent-lifecycle/lib/harness_adapter/<yourharness>.py`, implementing `detect_harness`/`parse_event`; (2) add a stable snake_case `HarnessName` enum entry in `base.py`; (3) register the adapter class in `dispatch.py`'s `ADAPTERS` list — order matters, more-specific detectors first, fallback adapters last; (4) write unit tests (`tests/unit/test_harness_adapter_<yourharness>.py` covering detect true/false and malformed-input → `[]`) plus one integration test in `tests/integration/test_harness_adapter_dispatch.py`; (5) no extra symlink step needed — `lib/harness_adapter/` is already a directory-level symlink to the `packages/` source of truth.
- **Canonical events:** `AgentStart` (carries `input_summary`, `tool_name`), `AgentEnd` (must set `exit_status` + `token_usage`), `ToolUse` (generic tool invocation), `TokenUsage` (accounting snapshot, often coincident with `AgentEnd`), `HeartbeatTick` (liveness, SLO 9, `alive=True`/`False`). Each event carries `agent_id` + `session_id` + event-specific fields (see `base.py` dataclasses).
- **Four safety rules:** never raise from `parse_event`/`detect_harness` (catch everything, return `[]`/`None`); treat raw input as hostile (`isinstance(raw, dict)` checks); no I/O in `detect_harness` (must be <1ms, synchronous); preserve event order on fan-out (e.g. `[AgentStart, AgentEnd]` in that order).
- **Test command:** `python3 -m pytest tests/unit/test_harness_adapter_*.py tests/integration/test_harness_adapter_dispatch.py -v`, target 100% pass across all adapters.
- **PR review checklist:** new adapter file present; `HarnessName` enum extended; `ADAPTERS` list updated in correct order; unit + integration tests present; no I/O/exceptions in `detect_harness`; malformed-input test present; ADR-033 referenced in commit message.
- **Live streaming (ADR-034), a second path on top of ADR-033:** post-hoc capture (hooks/file-close handlers) can't feed live consumers (TUI `cos-watch`, dashboards, MLflow bridge) — ADR-034 adds `ToolUseStart`, `ToolUseEnd`, `ProgressMarker` (parses `PROGRESS: [N/M] <message>`) live event types; `ToolUse`/`AgentEnd` from ADR-033 remain the post-hoc authoritative record.
- **`stream_events(source, poll_interval=0.5, stop_event=None, max_iterations=None)`:** generator signature yielding canonical live events; reference implementation `packages/agent-lifecycle/lib/harness_adapter/aider_streaming.py` tracks a byte offset per source to avoid duplicate reads.
- **Routing:** `cos-executor` daemon (`scripts/cos_executor.py`) subscribes to `cos:agent:*:*` and republishes on `cos:canonical:live`; adapters write via `AgentPublisher` or fall through to FallbackBus JSONL files.
- **Back-pressure:** Executor caps fan-out at 50 events/sec per project; adapters emitting faster should down-sample (e.g. every 10th token, every 500ms).
- **Portability rules:** prefer polling (`time.sleep`) over `inotify`/`fsevents`; track byte offsets per source and reset on file shrink/rotation; never raise out of the generator — exit silently on `stop_event` or IO errors.
- **Streaming tests:** parse fixed lines and verify event types/ordering; exercise `stop_event.set()` for clean generator return; exercise a second no-change call for no duplicate events.
- **Smoke signal:** the session banner flips from `Agent comms: FIRE_AND_FORGET (Valkey ✅, Executor ❌)` to `Agent comms: CONNECTED (Valkey ✅, Executor ✅)` when the Executor is live end-to-end.

## Relations & where used
- ADR-033 (harness-agnostic event capture) and ADR-034 (live streaming) — the architectural decisions this guide operationalizes.
- `packages/agent-lifecycle/lib/harness_adapter/` (symlinked to `lib/harness_adapter/`) — source-of-truth adapter directory; `claude_code.py` is cited as the reference post-hoc implementation, `aider_streaming.py` as the reference streaming implementation.
- `scripts/cos_executor.py` — the daemon that routes live adapter output to consumers.
- `dispatch.py` — the adapter registration point (`ADAPTERS` list).

## Status / caveats
- No explicit last-updated date; framed as an evergreen contributor guide tied to the (presumably stable) ADR-033/ADR-034 contract.
- Assumes familiarity with the base `HarnessAdapter` class and dataclasses defined in `base.py`, which is referenced but not included in this document.
