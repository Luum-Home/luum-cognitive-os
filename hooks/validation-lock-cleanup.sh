#!/usr/bin/env bash
# SCOPE: os-only
# validation-lock-cleanup.sh — SessionStart hook that removes stale validation locks.
#
# Per ADR-113 P5. Catches the common case where a session ended without trap
# firing (terminal closed, kernel panic, sleep+wake): the lock file remains
# but the owning process is gone or hung. This hook walks all *.lock files in
# .cognitive-os/runtime/, applies the 4-layer staleness check, and removes
# stale locks. Idempotent. Never blocks session start (always exits 0).
#
# Race-window protection: only removes locks whose started_at_epoch is >=60s
# old (avoids removing a lock another session is just starting).

set -uo pipefail

# Killswitch: respect the project-level disable flag.
if [ "${DISABLE_HOOK_VALIDATION_LOCK_CLEANUP:-false}" = "true" ]; then
  exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
LOG_FILE="$METRICS_DIR/validation-auto-recovery.jsonl"

[ -d "$RUNTIME_DIR" ] || exit 0

# Source the lock library for diagnosis
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB="$SCRIPT_DIR/_lib/validation-lock.sh"
[ -f "$LIB" ] || exit 0
# shellcheck source=/dev/null
source "$LIB"

mkdir -p "$METRICS_DIR" 2>/dev/null || true
CLEANED=0

shopt -s nullglob
# ADR-113 P5 scope: ONLY validation-capsule locks. Other subsystems (profile
# autoapply, circuit breaker, etc.) own their own locks with their own schemas
# and TTL semantics — they are NOT in scope for this hook.
for lock in "$RUNTIME_DIR"/validation-capsule*.lock; do
  [ -f "$lock" ] || continue
  command -v python3 >/dev/null 2>&1 || continue

  RESULT=$(python3 - "$lock" <<'PY'
import json, os, sys, time
from pathlib import Path

path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text())
except Exception:
    print("corrupt|0|0")
    sys.exit(0)

# Schema check: must have validation-capsule shape (run_id starting with letters
# + a capsule_dir field). Foreign locks bail out as "skip".
run_id = data.get("run_id") or ""
capsule_dir = data.get("capsule_dir") or ""
if not run_id or not capsule_dir:
    print("skip|0|not-validation-schema")
    sys.exit(0)

now = int(time.time())
started = int(data.get("started_at_epoch") or 0)
expires_at = int(data.get("expires_at_epoch") or 0)
pid = int(data.get("pid") or 0)
heartbeat = int(data.get("last_heartbeat_epoch") or 0)
hb_interval = int(data.get("heartbeat_interval_seconds") or 0)

# Race-window protection: don't touch locks <60s old
age = now - started if started else 0
if age < 60:
    print(f"young|{age}|{started}")
    sys.exit(0)

stale_signals = []
pid_is_alive = False
if expires_at and expires_at < now:
    stale_signals.append("ttl")
if pid > 0:
    try:
        os.kill(pid, 0)
        pid_is_alive = True
    except ProcessLookupError:
        stale_signals.append("pid")
    except PermissionError:
        pid_is_alive = True
if heartbeat > 0 and hb_interval > 0:
    if (now - heartbeat) > (3 * hb_interval):
        stale_signals.append("heartbeat")

# Activity check
activity_log = path.parent / "validation-activity.jsonl"
threshold = int(os.environ.get("COS_VALIDATION_ACTIVITY_THRESHOLD", "300"))
last_activity = 0
if activity_log.exists():
    try:
        with activity_log.open() as f:
            for line in f:
                try:
                    evt = json.loads(line)
                    ts_str = evt.get("ts", "")
                    if ts_str:
                        import calendar as _cal
                        ts = int(_cal.timegm(time.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")))
                        if ts > last_activity:
                            last_activity = ts
                except Exception:
                    continue
    except Exception:
        pass
# Activity is a secondary stale signal only when the owner PID is not alive.
# Long-running validation lanes may be quiet for > threshold while heartbeat is
# fresh; removing those locks deletes the active validation capsule mid-test.
if (not pid_is_alive) and last_activity > 0 and (now - last_activity) > threshold:
    stale_signals.append("activity")

if stale_signals:
    print(f"stale|{age}|{','.join(stale_signals)}")
else:
    print(f"healthy|{age}|0")
PY
)

  STATUS=$(echo "$RESULT" | cut -d'|' -f1)
  AGE=$(echo "$RESULT" | cut -d'|' -f2)
  DETAIL=$(echo "$RESULT" | cut -d'|' -f3)

  case "$STATUS" in
    stale)
      RUN_ID=$(python3 -c "import json,sys;d=json.load(open('$lock'));print(d.get('run_id','?'))" 2>/dev/null || echo "?")
      CAPSULE_DIR=$(python3 -c "import json,sys;d=json.load(open('$lock'));print(d.get('capsule_dir',''))" 2>/dev/null || echo "")
      rm -f "$lock"
      if [ -n "$CAPSULE_DIR" ] && [ -d "$CAPSULE_DIR" ]; then
        git -C "$PROJECT_DIR" worktree remove --force "$CAPSULE_DIR" >/dev/null 2>&1 || rm -rf "$CAPSULE_DIR"
      fi
      printf '{"ts":"%s","action":"auto_recovery","lock":"%s","run_id":"%s","age_seconds":%s,"stale_signals":"%s"}\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$lock" "$RUN_ID" "$AGE" "$DETAIL" >> "$LOG_FILE" 2>/dev/null || true
      CLEANED=$((CLEANED + 1))
      ;;
    corrupt)
      RUN_ID="(corrupt)"
      rm -f "$lock"
      printf '{"ts":"%s","action":"auto_recovery","lock":"%s","run_id":"%s","reason":"corrupt"}\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$lock" "$RUN_ID" >> "$LOG_FILE" 2>/dev/null || true
      CLEANED=$((CLEANED + 1))
      ;;
  esac
done

if [ "$CLEANED" -gt 0 ]; then
  echo "[validation-lock-cleanup] removed $CLEANED stale lock(s); see $LOG_FILE" >&2
fi

exit 0
