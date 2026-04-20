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
