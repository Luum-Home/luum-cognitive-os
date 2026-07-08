---
type: quality-synthesis
source: docs/09-Quality/manual-tests/claude-code-startup-hang-regression.md
provenance: "Manual regression test verifying the 2026-05-01 Claude Code startup hang / duplicate-first-prompt incident does not reproduce after SessionStart hardening (ADR-104 circuit breaker)."
---

## What it is
A manual regression procedure covering real Claude Code UI/CLI behavior that automated pytest can't fully simulate: new-conversation startup latency, duplicate first-prompt transcript blocks, subagent-shaped SessionStart fan-out, and hook stdout leaking into model context — plus explicit tests of the ADR-104 startup circuit breaker.

## Key mechanics
- Automated coverage that already exists for related surfaces: `tests/integration/test_sessionstart_subagent_scope.py`, `test_profile_drift_autoapply_flock.py`, `test_settings_atomic_write.py` — this manual test covers what those can't (actual UI behavior).
- Preconditions: run from repo root; unset 3 emergency opt-out env vars (`COS_DISABLE_PROFILE_AUTOAPPLY`, `COS_DISABLE_SUBAGENT_SESSIONSTART_SKIP`, `COS_DISABLE_HOOK_STDOUT_QUARANTINE`) so the regression path is actually exercised.
- Procedure: tail `.cognitive-os/metrics/hook-timing.jsonl` in a separate terminal; open a fresh Claude Code conversation; submit a short prompt that historically reproduced the issue; optionally trigger a subagent/Explore task; inspect the UI and timing log.
- Expected results: no multi-minute spinner; first user prompt appears exactly once (no duplicated transcript blocks); no `SessionStart` diagnostics leak into model-visible context; subagent-shaped SessionStart events log `session_kind: subagent, skipped: 1`; normal orchestrator startup logs `session_kind: orchestrator, skipped: 0`.
- Circuit breaker checks: ADR-104's startup circuit breaker is confirmed active when `hook-timing.jsonl` shows `safe_mode: 1, skipped: 1, skip_reason: startup_storm`. It can be force-tested via `scripts/cos-startup-recover.sh` without waiting for a real storm; during the TTL window, `SessionStart` records show `safe_mode=1`/`skipped=1` while PreToolUse safety hooks stay available. A manual kill switch exists via touching/removing `.cognitive-os/runtime/disable-sessionstart-hooks`.
- Failure triage: preserve the last 200 timing records to `/tmp/cos-hook-timing-startup-regression.jsonl`; scan for unskipped subagent SessionStart records via a small Python snippet; temporarily bypass autoapply with `COS_DISABLE_PROFILE_AUTOAPPLY=1 claude` if operator-blocking; if the regression only disappears with the new gate disabled, capture the hook input shape and extend `test_sessionstart_subagent_scope.py` before touching production logic.

## Relations & where used
Regression-tests ADR-104 (startup circuit breaker) and the SessionStart hardening it references; exercises `scripts/cos-startup-recover.sh`, `.cognitive-os/metrics/hook-timing.jsonl`, and the 3 integration test files named above.

## Status / caveats
Procedural manual-test document tied to a specific historical incident (2026-05-01) — it's a regression guard, not a dated report of a specific run's outcome. Requires live interactive Claude Code UI observation, which cannot be fully automated; the source itself acknowledges this limitation as the reason the test exists.
