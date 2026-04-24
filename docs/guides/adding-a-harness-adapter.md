# Adding a harness adapter

> Audience: contributors wiring a new agent harness (OpenCode, Cursor, Continue, a bespoke CLI, ...) into COS telemetry.
> Source of truth: ADR-033.

## The contract

An adapter translates one harness's native events into the canonical schema so downstream consumers (SLO watchdog, cost dashboard, error-learning) never see harness-specific shapes.

You implement **three methods**:

1. `detect_harness(raw) -> HarnessName | None` — classify a raw payload as yours or not.
2. `parse_event(raw) -> list[CanonicalEvent]` — translate one native payload into 0+ canonical events.
3. (optional) `emit_canonical` — override if you want a non-default output destination. The base implementation appends JSON lines to `.cognitive-os/metrics/canonical-events.jsonl`.

## Five-step recipe

### 1. Subclass `HarnessAdapter`

Create `packages/agent-lifecycle/lib/harness_adapter/<yourharness>.py`:

```python
from .base import (
    AgentStart, AgentEnd, ToolUse, HeartbeatTick,
    CanonicalEvent, HarnessAdapter, HarnessName, now_epoch,
)

class YourHarnessAdapter(HarnessAdapter):
    name = HarnessName.YOUR_HARNESS
    default_output = ".cognitive-os/metrics/canonical-events.jsonl"

    @classmethod
    def detect_harness(cls, raw):
        if isinstance(raw, dict) and raw.get("marker_unique_to_your_harness"):
            return cls.name
        return None

    def parse_event(self, raw):
        # Translate raw → canonical events. Return [] if nothing to emit.
        ...
```

### 2. Add the `HarnessName` value

Edit `base.py` and add your enum entry. Use a stable snake_case string:

```python
class HarnessName(str, Enum):
    ...
    YOUR_HARNESS = "your_harness"
```

### 3. Register in `dispatch.py`

```python
from .yourharness import YourHarnessAdapter

ADAPTERS = [
    ClaudeCodeAdapter,
    AiderAdapter,
    YourHarnessAdapter,   # add here
]
```

Order matters — more specific detection first. Put generic/fallback adapters last.

### 4. Write tests

Create `tests/unit/test_harness_adapter_<yourharness>.py`. At minimum:

- `detect_harness` returns your name for a known-good payload, `None` for foreign payloads.
- `parse_event` returns the canonical events you claim to produce.
- `parse_event` of malformed input returns `[]` without raising.

Add an end-to-end case in `tests/integration/test_harness_adapter_dispatch.py` exercising `dispatch_event`.

### 5. Symlink (if you created in `packages/`)

Files under `packages/*/lib/` are the source of truth; `lib/*` are symlinks. The existing `lib/harness_adapter/` is already a directory-level symlink, so new files you create under `packages/agent-lifecycle/lib/harness_adapter/` show up in `lib/harness_adapter/` automatically. No extra symlink step.

## Canonical events at a glance

| Event            | When to emit                                                    |
|------------------|-----------------------------------------------------------------|
| `AgentStart`     | New sub-agent begins. Carries `input_summary`, `tool_name`.     |
| `AgentEnd`       | Sub-agent terminates. Must set `exit_status` + `token_usage`.   |
| `ToolUse`        | Generic tool invocation (Read/Write/Bash/Grep/equivalent).      |
| `TokenUsage`     | Token accounting snapshot; often coincident with `AgentEnd`.    |
| `HeartbeatTick`  | Liveness tick (SLO 9). Emit `alive=True` on start, `False` end. |

Each event takes `agent_id` + `session_id` + event-specific fields. See `base.py` for dataclass signatures.

## Safety rules

1. **Never raise from `parse_event` or `detect_harness`.** Capture must not block a hook. Catch everything; return `[]` / `None`.
2. **Treat raw input as hostile.** It may be missing keys, have the wrong types, or be truncated. `isinstance(raw, dict)` checks are your friend.
3. **No I/O in `detect_harness`.** It must be synchronous and fast (< 1 ms). File reads belong in `parse_event`, inside a `try`.
4. **Preserve order when a raw event fans out.** If a harness emits start+end together, produce `[AgentStart, AgentEnd]` in that order.

## Running the test suite

```
python3 -m pytest tests/unit/test_harness_adapter_*.py tests/integration/test_harness_adapter_dispatch.py -v
```

Target: 100% pass, all adapters.

## Review checklist for the PR

- [ ] New adapter file in `packages/agent-lifecycle/lib/harness_adapter/`
- [ ] `HarnessName` enum extended
- [ ] `ADAPTERS` list in `dispatch.py` updated (correct order)
- [ ] Unit tests + one integration test case
- [ ] No I/O or exceptions in `detect_harness`
- [ ] Malformed-input test present
- [ ] ADR-033 referenced in the commit message

Questions? Start from ADR-033 (`docs/adrs/ADR-033-harness-agnostic-event-capture.md`) and the Claude Code reference implementation (`claude_code.py`).

## Live streaming (ADR-034)

Post-hoc capture (above) covers JSONL analysis. To also feed the live TUI (`cos-watch`), dashboards and MLflow bridge, implement the **streaming** path defined by ADR-034.

### Why a second path?

Post-hoc adapters are invoked by hooks / file-close handlers. Live consumers need events *as they happen*. ADR-034 adds three live event types on top of the ADR-033 schema:

| Event            | When to emit                                        |
|------------------|------------------------------------------------------|
| `ToolUseStart`   | Tool invocation has begun                            |
| `ToolUseEnd`     | Tool invocation has ended                            |
| `ProgressMarker` | Agent emitted `PROGRESS: [N/M] <message>`            |

`ToolUse` / `AgentEnd` from ADR-033 remain the post-hoc authoritative record.

### Implementing `stream_events`

Add a streaming variant (or extend your post-hoc adapter) with this signature:

```python
def stream_events(self, source, poll_interval=0.5,
                  stop_event=None, max_iterations=None):
    """Yield canonical live events as `source` produces them.

    - `source`: file path, fifo, or anything your harness streams to.
    - `poll_interval`: seconds between reads (portable polling).
    - `stop_event`: threading.Event; when set, the generator returns.
    - `max_iterations`: test hook; None = infinite.
    """
```

Reference: `packages/agent-lifecycle/lib/harness_adapter/aider_streaming.py`. It tracks a byte offset per source file so repeated reads do not duplicate events.

### Routing to consumers

The `cos-executor` daemon (`scripts/cos_executor.py`) subscribes to `cos:agent:*:*` and re-publishes normalised events on `cos:canonical:live`. Your adapter writes to `cos:agent:<id>:<suffix>` via `AgentPublisher` or falls through to the FallbackBus JSONL files — either way the daemon picks it up.

### Back-pressure

The Executor caps fan-out at **50 events/sec** per project. If your adapter can emit faster, down-sample before yielding (every 10th token, every 500 ms, …).

### Portability rules

- Prefer **polling** (`time.sleep`) over `inotify`/`fsevents` — runs unchanged on macOS, Linux and CI.
- Track a byte offset per source file; reset it when the file shrinks (rotation).
- Never raise out of the generator; exit silently on `stop_event` or IO errors.

### Tests

- `test_<harness>_streaming_adapter.py` — parse fixed lines, verify event types and ordering.
- Exercise `stop_event.set()` to prove the generator returns cleanly.
- Exercise a second call with no file change — no duplicate events.

### Banner feedback

When the Executor is running, the session banner flips from
`Agent comms: FIRE_AND_FORGET (Valkey ✅, Executor ❌)` to
`Agent comms: CONNECTED (Valkey ✅, Executor ✅)`. Use that as the smoke test that live streaming is live end-to-end.
