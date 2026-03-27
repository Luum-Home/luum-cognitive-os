# Orchestrator Mode — Subprocess-Based Delegation

## Activation

Set `ORCHESTRATOR_MODE=executor` to switch from the built-in Agent tool to
subprocess-based delegation via `ClaudeExecutor`.

**Default**: off (uses the Agent tool -- fire-and-forget).

## What Changes

| Capability | Agent Tool (default) | Executor Mode |
|------------|---------------------|---------------|
| Heartbeat monitoring | Not available | 5 s interval via Valkey |
| Progress streaming | Not available | Real-time tool-use events |
| Clarification Q&A | Not available | Pub/sub question/answer flow |
| File lock coordination | Not available | Via `lib/file_lock_registry` |
| Context isolation | Shared parent context | Fresh subprocess context |

## Trade-offs

* **Slower startup**: each agent spawns a new `claude` CLI process (~2-3 s).
* **Full control**: heartbeat timeout detection, progress tracking, coordinated
  file locking, and real-time visibility into sub-agent activity.
* **Cost parity**: token usage and model routing are identical.

## Usage

```bash
export ORCHESTRATOR_MODE=executor
```

In Python:

```python
from lib.orchestrator_mode import is_executor_mode, delegate_task

if is_executor_mode():
    result = delegate_task("Implement the new endpoint", model="sonnet")
```

## Integration

* `lib/orchestrator_mode.py` -- public API (`is_executor_mode`, `delegate_task`, `delegate_sdd_phase`)
* `lib/claude_executor.py` -- subprocess execution engine
* `lib/agent_bus.py` -- Valkey pub/sub communication
* `lib/file_lock_registry.py` -- distributed file locking
