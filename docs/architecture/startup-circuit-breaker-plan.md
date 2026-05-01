# Startup Circuit Breaker Implementation Plan

## Goal

Prevent Claude Code startup hangs, duplicate first prompts, and re-spawn loops from repeatedly executing mutating `SessionStart` hooks.

## Acceptance Criteria

1. `scripts/hook-timing-wrapper.sh` detects more than 3 `SessionStart` invocations within 20 seconds and writes `.cognitive-os/runtime/startup-safe-mode.json`.
2. While safe mode is active, `SessionStart` hook bodies are skipped and timing records include `safe_mode=1`, `skipped=1`, and a concrete `skip_reason`.
3. `COS_STARTUP_SAFE_MODE=1`, `COS_DISABLE_SESSIONSTART_HOOKS=1`, and `.cognitive-os/runtime/disable-sessionstart-hooks` each skip `SessionStart` hook bodies.
4. Expired safe mode files are ignored or removed, and normal orchestrator `SessionStart` still runs.
5. `scripts/cos-startup-recover.sh` activates bounded safe mode and cleans stale runtime/Git locks without deleting active Git locks when Git processes are running.
6. Existing hardening remains green: profile autoapply flock, atomic settings write, self-install behavior, session lifecycle.
7. Manual proof path is linked from docs.

## Implementation Steps

### Phase 1 — Wrapper circuit breaker

- Add constants/env parsing for threshold, window, TTL.
- Add runtime files:
  - `.cognitive-os/runtime/startup-circuit-breaker/events.jsonl`
  - `.cognitive-os/runtime/startup-circuit-breaker.lock`
  - `.cognitive-os/runtime/startup-safe-mode.json`
  - `.cognitive-os/runtime/disable-sessionstart-hooks`
- Add Python-backed helper inside wrapper for atomic event pruning and safe-mode writes.
- Skip `SessionStart` body when safe mode/manual disable is active.
- Extend timing JSON fields.

### Phase 2 — Recovery script

- Create `scripts/cos-startup-recover.sh`.
- Clean stale COS locks.
- Clean Git lock files only if no `git` process is detected.
- Activate safe mode with TTL.
- Print next-step commands.

### Phase 3 — Tests

- Extend `tests/integration/test_sessionstart_subagent_scope.py` or add a dedicated test file.
- Test storm activation.
- Test env safe mode.
- Test manual kill-switch file.
- Test expired safe mode.
- Test recovery script safe-mode file creation.
- Keep existing startup hardening tests green.

### Phase 4 — Documentation

- ADR-101 records decision.
- Manual test doc references circuit breaker behavior.
- Incident doc references ADR-101.

## Validation Commands

```bash
bash -n scripts/hook-timing-wrapper.sh scripts/cos-startup-recover.sh hooks/self-install.sh hooks/user-prompt-capture.sh
python3 -m pytest \
  tests/integration/test_sessionstart_subagent_scope.py \
  tests/integration/test_startup_circuit_breaker.py \
  tests/integration/test_profile_drift_autoapply_flock.py \
  tests/integration/test_settings_atomic_write.py \
  tests/behavior/test_self_install.py \
  tests/unit/test_session_lifecycle.py \
  -q
```
