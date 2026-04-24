# ADR-034 — Harness-Agnostic Live Agent Streaming

- **Status**: Proposed
- **Date**: 2026-04-20
- **Depends on**: ADR-033 (harness-agnostic event capture — merged as `c9f52bf`)
- **Owner**: Orchestrator runtime team
- **Supersedes**: none
- **Superseded by**: —

## 1. Context

ADR-033 standardised the **post-hoc** event capture path: every supported harness
(Claude Code, Aider, OpenCode, …) emits into a single canonical JSONL stream
(`.cognitive-os/metrics/canonical-events.jsonl`) via a pluggable
`HarnessAdapter` ABC. That solves "can I analyse a session after it
finished?", but leaves a visible UX gap:

| Dimension                                  | Status (pre-034)        |
|-------------------------------------------|-------------------------|
| Post-hoc metrics (JSONL)                  | ✅ ADR-033 canonical    |
| Valkey pub/sub bus                        | ✅ `lib/agent_bus.py`   |
| `OrchestratorSubscriber` API              | ✅                      |
| `PROGRESS: [N/M]` markers in sub-agent    | ✅ required by `rules/responsiveness.md` |
| **Executor daemon re-publishing live**    | ❌ banner reports OFF   |
| **Live consumer (CLI/TUI)**               | ❌ does not exist       |
| **Per-harness streaming adapter**         | ❌ CC hook-based only   |

Users of connected mode want the same affordance Claude Code's built-in
"agent panel" provides — elapsed time, cumulative tokens, tool count,
last 5 PROGRESS markers, last action — **but harness-agnostic**. The
banner line `Agent comms: FIRE_AND_FORGET (Valkey ✅, Executor ❌)` is the
surface symptom that no daemon is bridging Valkey ↔ consumer.

## 2. Decision

Introduce three components that together promote ADR-033's schema from a
write-only sink to a **live, subscribable stream**:

1. **`scripts/cos_executor.py`** — background daemon started at
   `SessionStart`, PID-locked like `hooks/reaper-heartbeat.sh`. It
   subscribes to the Valkey pattern `cos:agent:*:*` (or tails the
   `_FileFallback` JSONL when Valkey is down) and re-publishes
   **normalised live events** on the canonical stream
   `cos:canonical:live`. When running, it exports
   `ORCHESTRATOR_MODE=executor` for child processes via a state file so
   `orchestrator_capabilities.py` flips Executor to ✅.

2. **`scripts/cos_watch.py`** — TUI consumer. `cos-watch <agent_id>` or
   `cos-watch --latest`. Uses `rich.live` when available, falls back to
   a `\r`-refreshed plain-text panel. Shows: `agent_id`, elapsed,
   model, token usage (in/out/cache), tool count, last 5 `PROGRESS`
   markers, last tool used, status. Gracefully degrades to tailing
   `.cognitive-os/agent-bus/<id>/*.jsonl` when Valkey is down.

3. **`lib/harness_adapter/aider_streaming.py`** (POC) — extends
   `AiderAdapter` with a real-time `stream_events(history_file)` method
   that emits `ToolUseStart`/`ToolUseEnd`/`ProgressMarker` as the log
   grows (single-pass file position tracker; no `inotify` dependency —
   portable polling is sufficient for a POC).

### 2.1 Canonical live-event schema (extends ADR-033)

ADR-033 defines `AgentStart`, `AgentEnd`, `ToolUse`, `TokenUsage`,
`HeartbeatTick`. ADR-034 adds **three** event types for live UX. They
inherit `CanonicalEvent` (same `event_type` registry, same `to_dict` /
`from_dict` round-trip):

```python
@dataclass
class ToolUseStart(CanonicalEvent):
    event_type = "tool_use_start"
    agent_id: str = ""
    tool_name: str = ""
    started_at: float = 0.0
    tool_input_summary: Optional[str] = None  # ≤ 160 chars
    session_id: Optional[str] = None

@dataclass
class ToolUseEnd(CanonicalEvent):
    event_type = "tool_use_end"
    agent_id: str = ""
    tool_name: str = ""
    ended_at: float = 0.0
    duration_ms: int = 0
    exit_status: str = "success"   # success|error|timeout
    session_id: Optional[str] = None

@dataclass
class ProgressMarker(CanonicalEvent):
    event_type = "progress_marker"
    agent_id: str = ""
    ts: float = 0.0
    step_current: int = 0
    step_total: int = 0
    message: str = ""            # free-form "building foo"
    session_id: Optional[str] = None
```

`ToolUse` (ADR-033) is preserved as the **aggregated post-hoc** form;
`ToolUseStart` + `ToolUseEnd` are the live pair that any UI can fold
back into a `ToolUse` for persistence. This preserves backwards
compatibility — ADR-033 consumers see no change to their schema.

Live channel mapping:

| Live event      | Valkey channel                    | FallbackBus file            |
|-----------------|-----------------------------------|-----------------------------|
| `tool_use_start`| `cos:agent:{id}:tool_start`       | `{id}/tool_start.jsonl`     |
| `tool_use_end`  | `cos:agent:{id}:tool_end`         | `{id}/tool_end.jsonl`       |
| `progress_marker`| `cos:agent:{id}:progress` *(existing)* | `{id}/progress.jsonl` *(existing)* |
| `heartbeat_tick`| `cos:agent:{id}:heartbeat` *(existing)* | `{id}/heartbeat.jsonl` *(existing)* |

The Executor republishes **all** of the above on the aggregated
channel `cos:canonical:live` so a single `cos-watch` subscriber sees
every agent in the project.

## 3. Architecture

```
┌─────────────────┐    publishes      ┌──────────────┐
│ Any harness     │ ─── live events ─▶│ Valkey       │
│ (CC, Aider, …)  │                   │ (pub/sub)    │
│  via adapter    │                   └──────┬───────┘
└─────────────────┘                          │
          │                                  ▼
          │  fallback to       ┌─────────────────────────┐
          └──────────────────▶ │ FallbackBus JSONL files │
                               └────────────┬────────────┘
                                            │ tail
                                            ▼
                                   ┌──────────────────┐
                                   │ cos-executor.py  │  (PID-locked,
                                   │  daemon          │   started at
                                   └────────┬─────────┘   SessionStart)
                                            │ normalise + re-publish
                                            ▼
                                   ┌──────────────────┐
                                   │ cos:canonical:live│
                                   └────────┬─────────┘
                                            │
                          ┌─────────────────┼─────────────────┐
                          ▼                 ▼                 ▼
                   ┌─────────────┐   ┌────────────┐   ┌────────────────┐
                   │ cos-watch   │   │ Cost dash  │   │ MLflow bridge  │
                   │ (TUI)       │   │ (future)   │   │ (observability)│
                   └─────────────┘   └────────────┘   └────────────────┘
```

### 3.1 Executor single-instance guard

Pattern mirrors `hooks/reaper-heartbeat.sh`:

- PID file: `.cognitive-os/runtime/cos-executor.pid`
- `SIGTERM` handler: unlink PID file, unsubscribe, exit 0
- On start: if PID file exists and PID is alive → `sys.exit(0)` silently
- Stale PID file is removed

### 3.2 ORCHESTRATOR_MODE state flip

The daemon writes `.cognitive-os/runtime/orchestrator-mode` with the
value `executor` on successful startup and removes it on shutdown. The
existing `orchestrator-mode-detect.sh` (called at SessionStart) reads
**either** the env var **or** this state file to compute the banner.
This survives a shell that doesn't export the env var.

## 4. Alternatives considered

| # | Option | Rejected because |
|---|--------|------------------|
| A | Poll JSONL files every 500 ms from the TUI itself, no daemon | Every consumer re-implements tailing + rotation; N² fan-out once a cost-dash or MLflow bridge also want live |
| B | Scrape Claude Code's UI (accessibility API / TTY) | Fragile across versions; harness-specific — violates ADR-033 goal |
| C | **Daemon + pub/sub** (chosen) | Single producer → many consumers; reuses existing Valkey; consistent with ADR-033 |
| D | Embed TUI logic inside every harness adapter | Explodes adapter complexity; couples transport to presentation |

## 5. Rollout

| Wave | Deliverable | Gates |
|------|-------------|-------|
| W1 (this ADR) | schema + daemon + TUI + Aider POC + 3 tests | CI green; banner flips to ✅ when daemon running |
| W2            | OpenCode streaming adapter + Cursor adapter | reuse of Aider streaming pattern proven |
| W3            | Cost dashboard + MLflow bridge subscribe to `cos:canonical:live` | replaces JSONL polling |
| W4            | Soft-deprecate post-hoc-only mode for connected sessions | emit deprecation warning when Executor OFF + Valkey ON |

Feature flag: `runtime.live_streaming.enabled` (default `true` in
reconstruction/stabilization, `false` in production/maintenance until
W3 proven).

## 6. Consequences

**Easier:**
- Any consumer (TUI, cost, MLflow, web UI) subscribes to **one**
  channel instead of N harness-specific ones.
- New harnesses only implement `HarnessAdapter.stream_events()`; live
  UX comes for free.
- The banner's `Executor ✅` becomes a real, verifiable health signal.

**Harder:**
- One more background process to observe (mitigated by PID-file +
  heartbeat into `.cognitive-os/metrics/so-vitals.jsonl`).
- Adapter authors must decide between post-hoc (ADR-033) and live
  (ADR-034) semantics — resolved by: emit **both** where possible,
  daemon de-duplicates by `(agent_id, tool_name, started_at)`.

**Risk & mitigation:**
- *Valkey outage*: TUI falls back to FallbackBus tailing; daemon
  continues, re-publishes when Valkey is back.
- *Runaway event rate*: daemon enforces `MAX_EVENTS_PER_SEC = 50`,
  drops with a `WARN` line to `.cognitive-os/metrics/executor.log`.
- *Multiple sessions → multiple daemons*: PID file is per-project-dir,
  not per-session. Two sessions on the same project share one daemon
  (idempotent by design).

## 7. Acceptance criteria (test-anchored)

1. `docs/adrs/ADR-034-harness-agnostic-live-streaming.md` exists and
   contains sections 1-7 (this file).
2. `scripts/cos_executor.py --daemon` starts, writes PID file,
   replies `ALIVE` to `cos-executor.py --status`.
3. `scripts/cos_watch.py --agent-id test-123 --once` renders a single
   snapshot of a fed event stream without crashing (both rich and
   plain-text modes).
4. `pytest tests/integration/test_executor_publishes_live.py
   tests/integration/test_cos_watch_renders.py
   tests/unit/test_aider_streaming_adapter.py` — all pass.
5. With daemon running + `ORCHESTRATOR_MODE=executor` exported, the
   SessionStart banner reads
   `Agent comms: CONNECTED (Valkey ✅, Executor ✅)`.
6. `docs/guides/adding-a-harness-adapter.md` gains a "Live streaming"
   section explaining how to implement `stream_events()`.

## 8. References

- ADR-033 — Harness-agnostic event capture (`c9f52bf`)
- ADR-028  — Agent lifecycle SLOs (SLO 9 heartbeat subsystem split)
- `rules/responsiveness.md` — `PROGRESS: [N/M]` marker contract
- `rules/agent-communication.md` — Valkey channel namespacing
- `lib/agent_bus.py` — `OrchestratorSubscriber`, `_FileFallback`
- `hooks/reaper-heartbeat.sh` — PID-lock pattern reference
