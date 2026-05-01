# ADR-104 — Startup Circuit Breaker and Safe Mode

<!-- SCOPE: OS -->

**Status**: Accepted
**Date**: 2026-05-01
**Author**: Matias Nahuel Améndola
**Related**: ADR-086 (hook execution observability), ADR-088 (provenance markers), ADR-098 (multi-agent file coordination), `docs/incidents/2026-05-01-session-multi-spawn-hang.md`

## Status

Accepted for immediate implementation. The 2026-05-01 startup hang showed that individual hook fixes are necessary but not sufficient: the runtime needs a wrapper-level circuit breaker that can stop a startup storm even when a specific hook is broken or a harness repeatedly re-spawns sessions.

## Context

Claude Code treats `SessionStart` and `UserPromptSubmit` stdout as model context. It also watches project configuration files such as `.claude/settings.json`. A bad interaction can therefore create a positive feedback loop:

1. `SessionStart` hook writes watched state or blocks.
2. Harness re-spawns or retries startup.
3. The next session runs the same hooks again.
4. More writes/logs/context are emitted.
5. The UI shows duplicated first prompts or a multi-minute spinner.

The first hardening pass fixed the known concrete causes:

- same-filesystem atomic settings writes;
- non-blocking `profile-drift-autoapply` lock;
- subagent `SessionStart` skip;
- stdout quarantine for context-bearing events;
- non-blocking `self-install` git config repair lock.

Those fixes still assume the hook chain itself is healthy. The operator needs a more general safety layer: if `SessionStart` storms, the wrapper must stop running mutating startup hooks without requiring the user to know which hook failed.

## Decision

Add a startup circuit breaker to `scripts/hook-timing-wrapper.sh`, because every projected hook already passes through it.

### 1. Storm detector

For every `SessionStart` invocation, append a timestamped event to `.cognitive-os/runtime/startup-circuit-breaker/events.jsonl` under a best-effort lock.

Defaults:

| Setting | Default | Env override |
|---|---:|---|
| Window | 20 seconds | `COS_STARTUP_STORM_WINDOW_SECONDS` |
| Threshold | 3 `SessionStart` events | `COS_STARTUP_STORM_THRESHOLD` |
| Safe-mode TTL | 300 seconds | `COS_STARTUP_SAFE_MODE_TTL_SECONDS` |

When the count in the current window is greater than the threshold, write `.cognitive-os/runtime/startup-safe-mode.json` with `activated_at`, `expires_at`, and `reason=startup_storm`.

### 2. Safe mode

When safe mode is active, the wrapper skips `SessionStart` hook bodies before they can mutate files, launch daemons, acquire locks, or write model-visible stdout. The wrapper still logs timing metadata so the incident remains diagnosable.

Safe mode activates from any of:

- non-expired `.cognitive-os/runtime/startup-safe-mode.json`;
- `COS_STARTUP_SAFE_MODE=1`;
- `.cognitive-os/runtime/disable-sessionstart-hooks`;
- `COS_DISABLE_SESSIONSTART_HOOKS=1`.

Safe mode expires automatically after the TTL unless forced by env or kill-switch file.

### 3. Recovery script

Add `scripts/cos-startup-recover.sh` as the operator path for a blocked repo. It:

- creates runtime dirs;
- removes stale COS lock files;
- removes stale Git lock files only when no Git process appears active;
- activates safe mode for a bounded TTL;
- prints exact next commands for retry and diagnosis.

### 4. Observability

Extend `hook-timing.jsonl` records with:

- `session_kind`;
- `skipped`;
- `safe_mode`;
- `skip_reason`.

This lets future RCA distinguish normal hook execution from subagent gating, safe-mode suppression, and manual kill switch behavior.

## Consequences

### Positive

- A broken startup hook cannot keep re-running indefinitely during a re-spawn storm.
- Operators get one recovery command rather than a list of internals.
- The same logic applies to all projected `SessionStart` hooks without per-hook drift.
- Tests can exercise the real `.claude/settings.json` hook surface.

### Negative

- During safe mode, some startup affordances are temporarily missing: self-install sync, daemon launch, recovery banners, and startup context summaries.
- The first few events in a storm can still run before the threshold trips. Thresholds intentionally avoid false positives for legitimate resume/clear/compact behavior.

### Neutral

- Safe mode is advisory and local to the repo runtime directory.
- The wrapper remains best-effort; if filesystem writes fail, it falls back to hook execution unless explicit env safe mode is set.

## Alternatives rejected

| Alternative | Rejection reason |
|---|---|
| Add guard code to all 17 `SessionStart` hooks | High drift, easy to miss future hooks, higher maintenance. |
| Disable all hooks globally via existing killswitch | Too blunt; PreToolUse safety hooks should still work. |
| Rely on Claude Code hook timeouts | Timeouts do not stop re-spawn loops or repeated watched-file writes. |
| Make `profile-drift-autoapply` opt-in only | Reduces one cause but leaves generic startup storms unhandled. |

## Verification

- Unit/integration tests simulate repeated `SessionStart` invocations and assert safe mode activates.
- Tests assert manual kill-switch file and env flags skip `SessionStart` hook bodies.
- Tests assert expired safe mode does not suppress normal startup.
- Manual proof path: `docs/manual-tests/claude-code-startup-hang-regression.md`.

Runnable proof:

```bash
python3 -m pytest tests/unit/test_agent_runner.py tests/integration/test_startup_circuit_breaker.py -q
```

## Operator commands

Emergency bounded safe mode:

```bash
bash scripts/cos-startup-recover.sh
```

Manual safe mode for one launch:

```bash
COS_STARTUP_SAFE_MODE=1 claude
```

Disable only SessionStart hooks:

```bash
touch .cognitive-os/runtime/disable-sessionstart-hooks
```

Clear manual disable:

```bash
rm -f .cognitive-os/runtime/disable-sessionstart-hooks
```
