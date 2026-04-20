# ADR-033b — Duration Correlation and Aider Version Dispatch Hardening

**Status**: Accepted
**Date**: 2026-04-20
**Parent**: ADR-033 (`c9f52bf` — harness-agnostic event capture)
**Implements**: two known caveats left open in ADR-033

---

## Context — Caveats from ADR-033

ADR-033 established the harness-agnostic event capture ABC and shipped working
adapters for Claude Code and Aider. Two caveats were explicitly deferred:

### Caveat 1: `duration_ms` was aspirational

`ClaudeCodeAdapter._compute_duration_ms` in ADR-033 called a helper
`_duration_ms(raw, ts)` that attempted to read a `started_at` field from the
Post payload. Claude Code hook payloads do **not** include `started_at`. The
helper always returned `None`, making `AgentEnd.duration_ms` permanently `None`.

The correct approach is to correlate the Pre and Post events through the shared
`tool_use_id` that both carry.

### Caveat 2: Aider parser was brittle

The original `AiderAdapter.parse_event` used a single regex for all Aider
versions. Lines that did not match were silently skipped. As Aider added new
transcript patterns across versions (linting in 0.65, test runners in 0.70),
the adapter would silently drop those lines. Callers had no way to detect
parse failures.

---

## Decision

### 1. Duration via `tool_use_id` correlation

Introduce `CorrelationStore` in
`packages/agent-lifecycle/lib/harness_adapter/tool_use_correlation.py`:

- **On `PreToolUse:Agent`**: `CorrelationStore.record(tool_use_id, time.monotonic())`
- **On `PostToolUse:Agent`**: `CorrelationStore.pop(tool_use_id)` → compute
  `duration_ms = int((time.monotonic() - started) * 1000)`
- Returns `None` gracefully when no Pre was seen (e.g. process restart)

`ClaudeCodeAdapter` creates a `CorrelationStore` at construction time
(injectable for testing). The `_duration_ms` internal helper is removed;
replaced by `_compute_duration_ms(tool_use_id)`.

### 2. Aider version dispatch

`AiderAdapter.parse_event` now:

1. Detects the version from the first `#### aider vX.Y` header line.
2. Validates the version is in the supported range `>=0.60, <0.71`; raises
   `UnsupportedAiderVersion` if not (friendly error with the exact bounds).
3. Selects the per-version regex table via `_best_tool_re(version)`.
4. Emits a `ParseError` canonical event (added to `base.py`) for any non-blank,
   non-header line that matches no known pattern — no silent skips.

### 3. `ParseError` canonical event

Added to `base.py`:

```python
@dataclass
class ParseError(CanonicalEvent):
    event_type: ClassVar[str] = "parse_error"
    source_line: str = ""
    adapter: str = ""
    reason: str = ""
    session_id: Optional[str] = None
```

Consumers filtering on `event_type == "parse_error"` can detect unknown
transcript patterns and flag them for adapter updates.

---

## Correlation Store Design

```
PreToolUse:Agent payload
    │  tool_use_id = "tu-abc123"
    ▼
CorrelationStore.record("tu-abc123", time.monotonic())
    │
    │  ... agent runs for N ms ...
    ▼
PostToolUse:Agent payload
    │  tool_use_id = "tu-abc123"
    ▼
started = CorrelationStore.pop("tu-abc123")
duration_ms = int((time.monotonic() - started) * 1000)
    │
    ▼
AgentEnd(duration_ms=N)  ← real measurement
```

### Persistence for crash recovery

The store is backed by an append-only JSONL file at
`.cognitive-os/metrics/tool-use-correlation.jsonl`. On construction the file is
replayed (last-write-wins per ID). This ensures that if the Pre hook fires in
process A and the Post hook fires in a fresh process B, the correlation still
works.

### TTL cleanup

Entries older than 1 hour are pruned on each `record()` call. This bounds memory
and file growth in long sessions.

---

## Aider Versioning Strategy

| Version range | New patterns | Regex table |
|---|---|---|
| 0.60 – 0.64 | `Ran shell command`, `Applied edit`, `Saved file` | `_TOOL_BASE_RE` |
| 0.65 – 0.69 | adds `Linting …`, `Fixing …` | `_TOOL_065_RE` |
| 0.70 | adds `Running tests`, `Tests passed`, `Tests failed` | `_TOOL_070_RE` |

`_best_tool_re(version)` returns the most capable table that applies to the
detected version (best-effort: picks the highest threshold ≤ version). Unknown
versions (no header) fall back to `_TOOL_BASE_RE`.

The supported range pin `aider>=0.60,<0.71` is documented in the `aider.py`
module docstring and enforced by `_validate_version()`.

---

## Wave 2 Plan — Python API Migration

The current Aider adapter is a *passive file-watcher*: it reads lines from the
transcript file. This is a POC approach with two limitations:

1. It requires an external mechanism to tail the file and invoke the adapter.
2. Aider 0.70+ has a Python API (`aider.Coder`) that would allow direct
   event subscription without file watching.

**Wave 2** (not implemented in this ADR) will:

- Introduce an `AiderWatcher` daemon class that subscribes to `aider.Coder`
  events via the Python API.
- Deprecate the passive file-watcher in favour of the push model.
- Extend the version range constraint after validating the Python API across
  0.70+.
- Tracked as a separate task: `adr-033b-wave2-python-api-migration`.

---

## Verification

```bash
# AC 1: CorrelationStore CLI smoke-test
python3 -c "
from lib.harness_adapter.tool_use_correlation import CorrelationStore
import time
s = CorrelationStore()
s.record('abc', time.monotonic())
print(s.pop('abc'))
"

# AC 2: fixture files exist
ls tests/fixtures/aider-transcripts/

# AC 3: new unit tests
pytest tests/unit/test_tool_use_correlation.py \
       tests/unit/test_claude_code_duration.py \
       tests/unit/test_aider_version_dispatch.py -v

# AC 4: existing tests still pass
pytest tests/unit/test_harness_adapter_*.py \
       tests/integration/test_harness_adapter_*.py \
       tests/integration/test_native_agent_heartbeat.py -v

# AC 5: duration_ms correlation call in claude_code.py
grep -n 'duration_ms' packages/agent-lifecycle/lib/harness_adapter/claude_code.py

# AC 6: ADR doc
ls docs/adrs/ADR-033b-duration-correlation-and-aider-hardening.md
```

---

## Consequences

**Positive**:
- `AgentEnd.duration_ms` now reflects real wall-clock latency for agent tool calls.
- Aider parse failures are observable via `ParseError` events in the canonical stream.
- Version out-of-range is caught early with a clear error message rather than silent misbehaviour.
- The fixture corpus provides a regression baseline for all three tested Aider versions.

**Negative / trade-offs**:
- `CorrelationStore` adds a JSONL write on every Pre event. At high frequency
  (many parallel agents) this is a potential I/O bottleneck, mitigated by the
  fact that Pre/Post pairs are short-lived (seconds).
- The `aider>=0.60,<0.71` range will need a bump when Aider 0.71 releases.
  The `UnsupportedAiderVersion` exception will surface this immediately.
