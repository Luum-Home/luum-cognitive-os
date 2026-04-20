# Orchestrator Dogfood Smoke Test — Evidence

**Date**: 2026-04-20
**Commits**: `d176c07` (initial adapter + orchestrator), this commit (subscribe fix + docs)
**Test scope**: End-to-end validation that `scripts/orchestrator.py` launches a real sub-Claude via `ClaudeExecutor`, publishes heartbeats on the agent_bus, the `AgentBusMetrics` adapter bridges them to `MetricEvent` records, and the events persist to `.cognitive-os/metrics/agent-heartbeat.jsonl`.

## The self-hosting loop (now proven)

```
scripts/orchestrator.py run --task "..."
   └─> AutoExecutor.check_and_activate()          # ORCHESTRATOR_MODE=executor
        └─> Valkey reachable at localhost:6379    # confirmed
   └─> AgentBusMetrics().subscribe()
        ├─> on_heartbeat_event registered         # callback
        └─> OrchestratorSubscriber.subscribe_all() # psubscribe cos:agent:*:heartbeat + listener thread
   └─> ClaudeExecutor(agent_id=orch-XXX).run(prompt)
        ├─> AgentPublisher.start_heartbeat_thread() # publishes cos:agent:orch-XXX:heartbeat every 5s
        └─> subprocess.Popen([claude, -p, prompt, ...]) # real sub-Claude CLI
   └─> Sub-Claude runs, returns text
   └─> AgentPublisher._publish alive=False on stop()
   └─> OrchestratorSubscriber._handle_message routes to on_heartbeat_event
        └─> AgentBusMetrics.on_heartbeat_event emits MetricEvent to JSONL
   └─> .cognitive-os/metrics/agent-heartbeat.jsonl gains rows
   └─> scripts/so-vitals.sh later sees them via list_live/scan_stale
```

## Smoke test runs

All three runs used the real Claude Code CLI at `/Users/matias.nahuel.amendola/.local/bin/claude` v2.1.62, invoked via `CLAUDE_CODE_PATH=...` env var (the `claude` shell alias shadows it to a Mac .app which isn't subprocess-friendly).

### Run 1 — `--model haiku` (revealed 2 bugs)

```
$ CLAUDE_CODE_PATH=~/.local/bin/claude python3 scripts/orchestrator.py run \
    --task "Respond with exactly one word: PONG" --model haiku --timeout 90 --verbose
[orchestrator] executor mode=connected valkey=True
[orchestrator] subscriber start failed: agent_bus.OrchestratorSubscriber unavailable
[orchestrator] launching agent_id=orch-7663ba75 model=haiku
claude: There's an issue with the selected model (claude-haiku-3-5-20241022)...
agent_id:    orch-7663ba75
success:     False
elapsed:     5.50s
```

**Bugs found:**
1. **Subscriber import failed.** `from packages.agent_coordination.lib.agent_bus import ...` fails because Python cannot import a package name with hyphens. Fix: import through the `lib/agent_bus.py` symlink instead.
2. **Stale model mapping.** `lib/claude_executor.py:46` maps `haiku → claude-haiku-3-5-20241022`. The Claude CLI rejects that ID ("may not exist or you may not have access"). Fix deferred (model catalog issue, out of smoke-test scope).

Elapsed: 5.5s. Success: False (expected — model rejected).

### Run 2 — no `--model` (default, subscriber still broken)

```
$ CLAUDE_CODE_PATH=~/.local/bin/claude python3 scripts/orchestrator.py run \
    --task "Respond with exactly one word: PONG" --timeout 120 --verbose --show-text
[orchestrator] executor mode=connected valkey=True
[orchestrator] launching agent_id=orch-6bf5eeb5 model=default
claude: PONG
agent_id:    orch-6bf5eeb5
success:     True
elapsed:     10.14s
cost_usd:    0.0010
```

Sub-Claude answered correctly. No visible subscriber-start error (the orchestrator's exception path silenced it). But: `.cognitive-os/metrics/agent-heartbeat.jsonl` did NOT grow. Why? The subscriber was constructed but `on_heartbeat` only registered the callback — never called `subscribe_all()` to psubscribe the wildcard channel. Publisher broadcast heartbeats; no one received them.

**Bug 3 found:** `AgentBusMetrics.subscribe()` registered the callback but did NOT subscribe to the channel. Without `self._subscriber.subscribe_all()`, the OrchestratorSubscriber listener thread never started and the psubscribe never happened. Messages on `cos:agent:*:heartbeat` were dropped.

### Run 3 — fixes applied, full loop works

```
$ CLAUDE_CODE_PATH=~/.local/bin/claude python3 scripts/orchestrator.py run \
    --task "Respond with exactly one word: PONG" --timeout 120 --verbose
[orchestrator] executor mode=connected valkey=True
[orchestrator] launching agent_id=orch-278fe4a5 model=default
claude: PONG
agent_id:    orch-278fe4a5
success:     True
elapsed:     8.88s
cost_usd:    0.0010
```

`.cognitive-os/metrics/agent-heartbeat.jsonl` before: 1 row. After: **3 rows**. The 2 new rows:

```json
{"event_type":"agent_launched","payload":{"agent_id":"orch-278fe4a5","alive":true,"phase":"unknown","session_id":"orchestrator-orch-278fe4a5","tokens_used":0},"schema_version":1,"severity":"info","source":"agent_bus_metrics","timestamp":"2026-04-20T17:05:36+00:00"}
{"event_type":"agent_completed","payload":{"agent_id":"orch-278fe4a5","alive":false,"phase":"unknown","session_id":"orchestrator-orch-278fe4a5","tokens_used":0},"schema_version":1,"severity":"info","source":"agent_bus_metrics","timestamp":"2026-04-20T17:05:45+00:00"}
```

Evidence that every part of the chain fired:
- `source: agent_bus_metrics` → adapter did the emission, not the reverted `agent_heartbeat.py`.
- `event_type: agent_launched` on first heartbeat received → dedup table was empty, adapter wrote the transition.
- `event_type: agent_completed` 9 seconds later with `alive: false` → the stop signal flowed end-to-end.
- Only 2 events despite multiple 5-second heartbeats during the run → ADR-028b §1 dedup rule held (intermediate `alive=True` beats are silent, exactly as specified).

## Bugs found and fixed in this test

| # | File | Bug | Fix |
|---|---|---|---|
| 1 | `lib/agent_bus_metrics.py` | `from packages.agent_coordination...` fails — hyphens in dir name | Import via `lib.agent_bus` symlink |
| 2 | `lib/claude_executor.py:46` | `haiku` mapped to stale model ID `claude-haiku-3-5-20241022` | Deferred (out of scope) |
| 3 | `lib/agent_bus_metrics.py` `subscribe()` | Registered callback but never called `subscribe_all()` — listener never ran | Added `self._subscriber.subscribe_all()` after `on_heartbeat()` |
| 4 | `scripts/orchestrator.py` | Called non-existent `subscriber.start()` method | Simplified to just `abm.subscribe()` (which now subscribes internally) |

## Reproducibility

To re-run on a fresh checkout:

```bash
# Prereqs: Valkey running (localhost:6379), claude CLI at ~/.local/bin/claude
bash scripts/so-vitals.sh | grep -i valkey  # confirm REACHABLE

# Baseline
wc -l .cognitive-os/metrics/agent-heartbeat.jsonl

# Smoke test (~10s, ~$0.001)
CLAUDE_CODE_PATH=$HOME/.local/bin/claude python3 scripts/orchestrator.py run \
    --task "Respond with exactly one word: PONG" --timeout 120 --verbose

# Verify events landed
wc -l .cognitive-os/metrics/agent-heartbeat.jsonl   # +2 rows
tail -2 .cognitive-os/metrics/agent-heartbeat.jsonl \
    | python3 -c "import sys, json; [print(json.loads(l)['event_type']) for l in sys.stdin]"
# Expected: agent_launched / agent_completed

# Observe via so-vitals while the agent is still alive (run another invocation in a 2nd shell)
bash scripts/so-vitals.sh | grep Agents
# Expected: "Agents: 1 in flight, 0 stale" during the run
```

## Remaining gaps (honest list)

- **Model-catalog refresh**: `lib/claude_executor.MODEL_MAP` has stale Anthropic model IDs. `haiku` is unusable today; `sonnet` / `opus` may also drift. Not a blocker for dogfooding (default works), but the `--model` shortname was advertised and currently lies.
- **Phase field is "unknown"**: the sub-Claude's AgentPublisher doesn't know what phase it's in (no external tag). Fine for observability, but `phase` field in MetricEvent is always "unknown" unless the agent explicitly publishes a phase via `publisher.heartbeat(phase=...)`.
- **No heartbeat.jsonl in FallbackBus for this run**: because Valkey was connected, publishers went over pub/sub which is ephemeral. If Valkey goes down mid-run, we'd lose real-time heartbeats until the FallbackBus kicks in. Failover tested only in unit contracts.
- **Cost recording is thin**: `$0.0010` comes from `claude_executor._calculate_cost` using `MODEL_COSTS`. Token counts showed `0/0` because the CLI didn't stream them out under `stream-json` in this invocation (or the parser missed them). Needs investigation — separate issue.
- **`agent_bus_metrics` is not wired as a hook**. The adapter runs in-process with the orchestrator. For ambient monitoring (any sub-Claude launched by anything, not just our script), we'd need a long-running subscriber daemon. That's Phase B territory.

## What this commit adds to ADR-028

ADR-028 Pilar 1 (runtime observability):
- ✅ D1.A metrics census + MetricEvent + rotation
- ✅ D1.B process registry + reaper
- ✅ **D1.C — agent heartbeat as agent_bus adapter (now PROVEN end-to-end)**
- ✅ D1.D so-vitals dashboard (now consumes the adapter)

**Pilar 1 closed.** Dogfooding loop verified. Self-hosting the OS via `scripts/orchestrator.py` instead of the native Agent tool is now a concrete option.

## Commits
| SHA | Change |
|---|---|
| `d176c07` | Adapter + orchestrator (initial, subscriber half-wired) |
| (this) | `subscribe()` calls `subscribe_all()` + report |
