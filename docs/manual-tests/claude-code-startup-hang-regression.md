# Manual Test: Claude Code Startup Hang Regression

Purpose: verify the 2026-05-01 Claude Code startup hang/duplicate-prompt incident does not reproduce in `luum-agent-os` after the SessionStart hardening.

## Scope

This manual test covers the real Claude Code UI/CLI behavior that cannot be fully simulated by pytest:

- New conversation startup latency.
- Duplicate first prompt/transcript blocks in the chat UI.
- Subagent-shaped SessionStart fan-out.
- Hook stdout accidentally entering model context.

Automated coverage lives in:

- `tests/integration/test_sessionstart_subagent_scope.py`
- `tests/integration/test_profile_drift_autoapply_flock.py`
- `tests/integration/test_settings_atomic_write.py`

## Preconditions

Run from the repo root:

```bash
cd <repo-root>
```

Optional emergency opt-outs must be unset for the regression test:

```bash
unset COS_DISABLE_PROFILE_AUTOAPPLY
unset COS_DISABLE_SUBAGENT_SESSIONSTART_SKIP
unset COS_DISABLE_HOOK_STDOUT_QUARANTINE
```

## Procedure

1. Clear old timing noise or record the current end of the file:

   ```bash
   mkdir -p .cognitive-os/metrics
   tail -n 5 .cognitive-os/metrics/hook-timing.jsonl 2>/dev/null || true
   ```

2. In a separate terminal, watch hook timing:

   ```bash
   tail -f .cognitive-os/metrics/hook-timing.jsonl
   ```

3. Open a fresh Claude Code conversation in this repo.

4. Submit a short prompt that previously reproduced the issue, for example:

   ```text
   hola, resumime el estado del repo en una frase
   ```

5. If the workflow uses subagents, trigger one lightweight Agent/Explore task from Claude Code.

6. Inspect the UI and timing log.

## Expected Result

- The new conversation becomes usable without a multi-minute spinner.
- The first user prompt appears once, not duplicated as repeated blue transcript blocks.
- `SessionStart` diagnostics do not appear as model-visible context.
- If subagent-shaped SessionStart events occur, timing records include:

  ```json
  "session_kind": "subagent",
  "skipped": 1
  ```

- Normal orchestrator startup records include:

  ```json
  "session_kind": "orchestrator",
  "skipped": 0
  ```


## Circuit Breaker Checks

The ADR-101 startup circuit breaker is active when any of these records appear in `.cognitive-os/metrics/hook-timing.jsonl`:

```json
"safe_mode": 1,
"skipped": 1,
"skip_reason": "startup_storm"
```

To intentionally test bounded safe mode without waiting for a real storm:

```bash
bash scripts/cos-startup-recover.sh
tail -f .cognitive-os/metrics/hook-timing.jsonl
```

Open a fresh Claude Code conversation. During the TTL window, `SessionStart` hook records should show `safe_mode=1` and `skipped=1`; PreToolUse safety hooks remain available.

Manual kill switch for `SessionStart` only:

```bash
touch .cognitive-os/runtime/disable-sessionstart-hooks
# clear after verification
rm -f .cognitive-os/runtime/disable-sessionstart-hooks
```

## Failure Triage

If the hang or duplicate prompt returns:

1. Preserve the last 200 timing records:

   ```bash
   tail -200 .cognitive-os/metrics/hook-timing.jsonl > /tmp/cos-hook-timing-startup-regression.jsonl
   ```

2. Check for unskipped subagent SessionStart records:

   ```bash
   python3 - <<'PY'
import json
from pathlib import Path
p = Path('.cognitive-os/metrics/hook-timing.jsonl')
for line in p.read_text().splitlines()[-200:]:
    try:
        r = json.loads(line)
    except Exception:
        continue
    if r.get('event') == 'SessionStart' and r.get('session_kind') == 'subagent' and r.get('skipped') != 1:
        print(r)
PY
   ```

3. Temporarily bypass autoapply if the session is operator-blocking:

   ```bash
   COS_DISABLE_PROFILE_AUTOAPPLY=1 claude
   ```

4. If the regression only disappears when disabling the new gate, capture the hook input shape and update `tests/integration/test_sessionstart_subagent_scope.py` before changing production logic.
