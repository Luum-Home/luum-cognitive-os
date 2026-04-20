# ADR-028b — Addendum: D1.C Replanned Around agent_bus

**Status**: Addendum to ADR-028
**Date**: 2026-04-20
**Supersedes**: ADR-028 D1.C (original spec, lines 166–214)
**Amends**: ADR-028a §2 (consumer-boundary table, updated below)

---

## Why This Addendum Exists

ADR-028 D1.C proposed a parallel heartbeat system writing
`.cognitive-os/tasks/{agent_id}.heartbeat` files every 60 s.
The implementation (commit `3d03419`) was reverted (`8eb57b2`) because
it duplicated `lib/agent_bus.py`, which already provides:

- Channel `cos:agent:{id}:heartbeat` published every **5 s** via
  `AgentPublisher.start_heartbeat_thread()` (line 468,
  `lib/agent_bus.py`).
- `alive: True` on every periodic beat; `alive: False` on
  `AgentPublisher.stop()` (line 497) and `report_complete()` (line 443).
- Valkey pub/sub transport with automatic fallback to JSONL files under
  `.cognitive-os/agent-bus/{agent_id}/heartbeat.jsonl` via
  `_FileFallback` (line 134).
- `OrchestratorSubscriber._agent_heartbeats` dict (line 535) that tracks
  the last heartbeat per agent in memory.

Existing consumers: `lib/claude_executor.py` calls
`AgentPublisher.start_heartbeat_thread()` at line 267;
`lib/agent_dashboard.py` constructs `OrchestratorSubscriber` at line 201
and registers `_on_heartbeat` at line 202.

Root cause: ADR-028 D1.C was written without grepping the codebase for
existing heartbeat infrastructure. Same class of bug as the ADR-028
hook-health `~40%` false claim corrected in ADR-028a §5.1.

---

## Revised D1.C Scope

### What `lib/agent_bus.py` Already Provides

| Capability | Detail |
|---|---|
| Heartbeat transport | `cos:agent:{id}:heartbeat` channel, 5 s cadence |
| Progress transport | `cos:agent:{id}:progress` channel, per tool use |
| Bidirectional signaling | `cos:agent:{id}:question` / `cos:agent:{id}:answer` |
| Control commands | `cos:agent:{id}:control` — `stop`, `pause`, `resume` |
| Valkey pub/sub | Primary path; `is_valkey_available()` check at line 100 |
| File fallback | `_FileFallback` writes `agent-bus/{id}/{channel}.jsonl`; `read_events()` reads them back |
| In-memory state | `OrchestratorSubscriber._agent_heartbeats[agent_id]` — last heartbeat per agent |
| Liveness signal | `alive: False` on `stop()` and `report_complete()` |

### What Was Missing (the Actual D1.C Goal)

The following gaps are not addressed by `agent_bus.py` in its current
form and remain valid D1.C deliverables:

1. **Offline MetricEvent emission.** `agent_bus` publishes in real time
   but does not append `MetricEvent` rows to a JSONL file. Watchdog
   tooling, `so-vitals.sh`, and trend analysis (e.g., hang rate over
   time) need durable records. `lib/metric_event.append_event()` (line
   108, `lib/metric_event.py`) is the canonical write path.

2. **Stale-heartbeat detection.** `OrchestratorSubscriber` tracks the
   last heartbeat in memory but does not scan for agents whose
   `last_beat` has not been updated beyond a configurable threshold.
   Detection must work across session boundaries (memory is transient;
   FallbackBus files persist).

3. **so-vitals integration.** `scripts/so-vitals.sh` currently reports 0
   agents in flight (no agent-count code path exists in the script).
   After the adapter lands, it must count live agents using the same
   infrastructure `agent_bus` already writes.

### Revised Artifacts

Do NOT create:
- `lib/agent_heartbeat.py` (deleted; was the reverted implementation)
- `hooks/_lib/heartbeat.sh` (deleted)
- `.cognitive-os/tasks/{agent_id}.heartbeat` file path (deprecated path)

DO create:

#### 1. `lib/agent_bus_metrics.py` — thin adapter

Subscribes to heartbeat events from `agent_bus` and bridges them to
durable `MetricEvent` records. Public API contract:

```python
class AgentBusMetrics:
    """Adapter that bridges agent_bus heartbeats to MetricEvent JSONL records.

    Uses OrchestratorSubscriber when Valkey is available; reads FallbackBus
    JSONL files when Valkey is not reachable. Both paths produce identical
    MetricEvent output.

    Args:
        metrics_path: Path to the JSONL sink.
                      Defaults to .cognitive-os/metrics/agent-heartbeat.jsonl.
        valkey_url: Redis-compatible URL.
        fallback_dir: FallbackBus base directory.
                      Defaults to .cognitive-os/agent-bus.
        stale_threshold_seconds: Seconds without a heartbeat before an
                                 agent is considered stale. Default 300.
    """

    def on_heartbeat_event(self, data: dict) -> None:
        """Callback registered with OrchestratorSubscriber.on_heartbeat().

        Emits MetricEvent(event_type="agent_launched") on the first
        heartbeat from a previously unseen agent_id.
        Emits MetricEvent(event_type="agent_completed") when alive==False.
        No-op on subsequent alive==True beats (transport already recorded
        in _agent_heartbeats; MetricEvent for intermediate beats is waste).
        """

    def scan_stale(self, max_age_seconds: int = 300) -> list[dict]:
        """Return agents whose last heartbeat is older than max_age_seconds.

        When Valkey is available: queries OrchestratorSubscriber._agent_heartbeats
        in-memory dict and compares timestamp_epoch to time.time().
        When Valkey is unavailable: reads FallbackBus files under
        .cognitive-os/agent-bus/{agent_id}/heartbeat.jsonl, takes the
        last record per agent, and compares timestamp_epoch to time.time().

        Returns a list of dicts:
            [{"agent_id": str, "last_beat_epoch": float,
              "age_seconds": float, "last_phase": str}, ...]
        """

    def list_live(self) -> list[dict]:
        """Return agents with a heartbeat in the last stale_threshold_seconds.

        Same data source as scan_stale(); returns the complement set.
        """

    def mark_hung_and_publish(self, agent_id: str) -> None:
        """Mark an agent as hung and signal it to stop.

        1. Appends MetricEvent(event_type="agent_hung") to the JSONL sink.
        2. Publishes "stop" to cos:agent:{agent_id}:control via
           AgentPublisher._publish("control", {"command": "stop"}).
           Falls back to FallbackBus write when Valkey is unavailable.
        """
```

`MetricEvent` fields used:

| Field | Value |
|---|---|
| `event_type` | `agent_launched`, `agent_completed`, `agent_hung` |
| `source` | `agent_bus_metrics` |
| `service` | `agent_id` |
| `session_id` | value from `data["session_id"]` if present, else `""` |
| `details` | `{"phase": str, "alive": bool, "tokens_used": int}` |

All events written via `lib.metric_event.append_event()`.

#### 2. `scripts/so-agent-status.sh` — CLI listing live agents

Reads from `lib/agent_bus_metrics.list_live()` and `scan_stale()`. Does
NOT scan `.cognitive-os/tasks/`. Example output format:

```
AGENT ID          PHASE        AGE(s)  STATE
────────────────────────────────────────────
abc123-apply      apply          12    live
def456-verify     verify        312    STALE
```

Uses `python3 -c "from lib.agent_bus_metrics import AgentBusMetrics; ..."`.
Exits 0 when any live agents exist, exits 1 when none.

#### 3. `scripts/so-vitals.sh` — agent-count integration (minor change)

`scripts/so-vitals.sh` currently shows 0 agents in flight. After the
adapter lands, the agent-count line should call
`AgentBusMetrics().list_live()` to populate that value. No structural
change to `so-vitals.sh`; one function call replaces the hard-coded zero.

#### 4. `tests/contracts/test_agent_bus_metrics.py` — contract tests

Four scenarios, each runnable without a live Valkey instance
(FallbackBus path):

| Test | Assert |
|---|---|
| `test_first_heartbeat_emits_launched_event` | `on_heartbeat_event` with `alive=True` from an unseen agent → exactly one `agent_launched` MetricEvent in JSONL |
| `test_alive_false_emits_completed_event` | `on_heartbeat_event` with `alive=False` → exactly one `agent_completed` MetricEvent |
| `test_scan_stale_honors_threshold` | After writing a FallbackBus heartbeat file with `timestamp_epoch = time.time() - 400`, `scan_stale(300)` returns that agent |
| `test_mark_hung_emits_event_and_publishes_stop` | `mark_hung_and_publish(agent_id)` → JSONL contains `agent_hung` event AND FallbackBus `control.jsonl` contains `{"command": "stop"}` |
| `test_fallback_path_when_valkey_unreachable` | Constructing `AgentBusMetrics(valkey_url="redis://127.0.0.1:19999")` does not raise; `list_live()` reads FallbackBus files successfully |

---

## Out of Scope for D1.C

- Re-implementing what `agent_bus.py` already provides: transport,
  channel names, pub/sub subscription, Valkey connection management.
- Modifying the `cos:agent:{id}:heartbeat` message schema (the existing
  `alive`, `phase`, `step`, `tokens_used`, `timestamp_epoch` fields are
  sufficient).
- Modifying `lib/claude_executor.py` — it already integrates with
  `AgentPublisher` at line 267; no change needed.
- Modifying `lib/agent_dashboard.py` — it already consumes heartbeats
  via `OrchestratorSubscriber`; the adapter is additive.

---

## Deprecated Artifacts (Do Not Recreate)

| Artifact | Reason |
|---|---|
| `lib/agent_heartbeat.py` | Reverted in `8eb57b2`; duplicated `AgentPublisher` |
| `hooks/_lib/heartbeat.sh` | Reverted; agents heartbeat via `AgentPublisher.start_heartbeat_thread()`, not a shell cron |
| `hooks/_lib/agent-preamble.md` | Canonical preamble lives in `templates/agent-preamble.md`; the hooks lib copy was a stale duplicate |
| `.cognitive-os/tasks/{agent_id}.heartbeat` | Replaced by FallbackBus path `.cognitive-os/agent-bus/{agent_id}/heartbeat.jsonl` |

---

## Integration With Existing Addenda

### ADR-028a §2 — WS13 vs D1.C consumer-boundary table

ADR-028a §2 defined a consumer-boundary table that assigned
`.cognitive-os/tasks/{agent_id}.heartbeat` to D1.C. That file path is
now deprecated. The table's intent is preserved with the corrected
source:

| Question | Canonical source | File |
|---|---|---|
| "Is this session still alive?" | WS13 snapshot timestamp | `.cognitive-os/sessions/{id}/state-snapshot.json` |
| "Is agent X still running?" | `AgentBusMetrics.list_live()` → FallbackBus | `.cognitive-os/agent-bus/{agent_id}/heartbeat.jsonl` |
| "What was in progress when the session died?" | WS13 snapshot content | `.cognitive-os/sessions/{id}/state-snapshot.json` |
| "Which agents are hung right now?" | `AgentBusMetrics.scan_stale()` | Same FallbackBus file, filtered by age |

`hooks/crash-recovery.sh` reads only `state-snapshot.json`.
`AgentBusMetrics` reads only `agent-bus/` files (or Valkey).
The separation of concerns from ADR-028a §2 is unchanged; only the
file path on the D1.C side is corrected.

### ADR-028 D4 — WS11 / Bug 1

Unchanged. WS11 disable and its global-verify.sh replacement (ADR-028a
§1) are independent of the heartbeat implementation.

### ADR-028 D1.A — MetricEvent schema

`lib/agent_bus_metrics.py` uses `lib.metric_event.append_event()` — the
same write path defined in D1.A.1. D1.A.0 (fix missing-file write path,
ADR-028a §5.3 / F-4) is a prerequisite: if `SESSION_ID` propagation is
broken, `agent-heartbeat.jsonl` may also fail to land on disk. Execute
D1.C after D1.A.0 acceptance criteria are met.

---

## Lessons

This is the second ADR-028 scope error caught before execution:

1. ADR-028a §5.1 — F-1: `hook-health.jsonl` claimed `~40%` unparseable;
   actual count: 0 bad rows.
2. This addendum: D1.C proposed a parallel heartbeat channel without
   checking whether one already existed.

Both errors share the same root cause: the ADR was written against a
mental model of the codebase, not a discovery pass over actual files.

Mitigation adopted going forward: every ADR section that introduces
new infrastructure must include a **"Discovery pass"** subsection that
lists relevant existing files found by `grep` or `Glob` before defining
new artifacts. If a discovery pass is absent, the section is considered
incomplete and must be revised before the corresponding execution phase
is launched. See the proposed `reinvention-check.sh` hook wiring
(separate work).

---

## Action Items

- [ ] Create `lib/agent_bus_metrics.py` per the API contract above
      (separate implementation task; this ADR is planning only).
- [ ] Update `scripts/so-vitals.sh` agent-count code path to call
      `AgentBusMetrics().list_live()` once the adapter lands.
- [ ] Prefix ADR-028 D1.C original text (lines 166–214) with:
      `> **Superseded by ADR-028b.** See docs/adrs/ADR-028b.md.`
- [ ] Update ADR-028a §2 consumer-boundary table to reference
      `.cognitive-os/agent-bus/{agent_id}/heartbeat.jsonl` instead of
      `.cognitive-os/tasks/{agent_id}.heartbeat`.
- [ ] Replace work-queue item `d1a1-metric-event` next-phase reference
      with `d1c-agent-bus-adapter` once D1.A.0 is complete and the
      MetricEvent write path is confirmed stable on disk.
- [ ] Verify D1.A.0 acceptance criteria pass before executing D1.C
      (the JSONL sink depends on the fixed write-path from F-4).
