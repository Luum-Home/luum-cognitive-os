#!/usr/bin/env bash
# SCOPE: both
# validation-lock.sh — shared validation capsule lock helpers.

# Return 0 when PROJECT_DIR has an active validation capsule lock.
# Stale locks (expired or dead holder pid) are removed best-effort and return 1.
cos_validation_lock_active() {
  local project_dir="${1:-${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}}"
  local lock_file="$project_dir/.cognitive-os/runtime/validation-capsule.lock"

  [ -f "$lock_file" ] || return 1
  [ "${COS_VALIDATION_CAPSULE_ACTIVE:-0}" = "1" ] && return 1
  [ "${COS_VALIDATION_ALLOW_CONCURRENT_AGENTS:-0}" = "1" ] && return 1

  if command -v python3 >/dev/null 2>&1; then
    python3 - "$lock_file" <<'PY'
import json
import os
import sys
import time
from pathlib import Path

path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text())
except Exception:
    # Unknown lock shape: fail closed while the file exists.
    sys.exit(0)

now = int(time.time())
expires_at = int(data.get("expires_at_epoch") or 0)
pid = int(data.get("pid") or 0)
heartbeat = int(data.get("last_heartbeat_epoch") or 0)
hb_interval = int(data.get("heartbeat_interval_seconds") or 0)

stale = False
# ADR-108 layer 1: TTL fail-safe
if expires_at and expires_at < now:
    stale = True
# ADR-108 layer 2: PID liveness
elif pid > 0:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        stale = True
    except PermissionError:
        stale = False

# ADR-108 layer 3: heartbeat staleness (3 missed beats == dead)
if not stale and heartbeat > 0 and hb_interval > 0:
    if (now - heartbeat) > (3 * hb_interval):
        stale = True

# ADR-108 layer 4: activity staleness (semantic check, 5 min default)
if not stale:
    activity_log = path.parent / "validation-activity.jsonl"
    activity_threshold = int(os.environ.get("COS_VALIDATION_ACTIVITY_THRESHOLD", "300"))
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
    if last_activity > 0 and (now - last_activity) > activity_threshold:
        stale = True

if stale:
    try:
        path.unlink()
    except Exception:
        pass
    sys.exit(1)

sys.exit(0)
PY
    return $?
  fi

  # Without python, treat an existing lock as active. This is safer than
  # allowing new agents to mutate a validating worktree.
  return 0
}

# ADR-108 P3: report a structured staleness diagnosis for status command.
# Outputs one line per signal: "<signal>=<state> [<detail>]".
# Signals: ttl, pid, heartbeat, activity. State: ok|stale|missing.
cos_validation_lock_stale_reason() {
  local project_dir="${1:-${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}}"
  local lock_file="$project_dir/.cognitive-os/runtime/validation-capsule.lock"
  [ -f "$lock_file" ] || { echo "lock=missing"; return 0; }
  command -v python3 >/dev/null 2>&1 || { echo "python3=missing"; return 0; }
  python3 - "$lock_file" <<'PY'
import json, os, sys, time
from pathlib import Path

path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text())
except Exception:
    print("lock=corrupt")
    sys.exit(0)

now = int(time.time())
expires_at = int(data.get("expires_at_epoch") or 0)
pid = int(data.get("pid") or 0)
heartbeat = int(data.get("last_heartbeat_epoch") or 0)
hb_interval = int(data.get("heartbeat_interval_seconds") or 0)

# TTL
if expires_at:
    remaining = expires_at - now
    if remaining < 0:
        print(f"ttl=stale [expired {-remaining}s ago]")
    else:
        print(f"ttl=ok [{remaining}s remaining]")
else:
    print("ttl=missing")

# PID
if pid > 0:
    try:
        os.kill(pid, 0)
        print(f"pid=ok [{pid} alive]")
    except ProcessLookupError:
        print(f"pid=stale [{pid} not found]")
    except PermissionError:
        print(f"pid=ok [{pid} alive (permission denied to signal)]")
else:
    print("pid=missing")

# Heartbeat
if heartbeat > 0 and hb_interval > 0:
    age = now - heartbeat
    threshold = 3 * hb_interval
    if age > threshold:
        print(f"heartbeat=stale [{age}s old, threshold {threshold}s]")
    else:
        print(f"heartbeat=ok [{age}s old, interval {hb_interval}s]")
elif heartbeat == 0 and hb_interval == 0:
    print("heartbeat=missing [legacy lock]")
else:
    print(f"heartbeat=incomplete [hb={heartbeat} interval={hb_interval}]")

# Activity
activity_log = path.parent / "validation-activity.jsonl"
threshold = int(os.environ.get("COS_VALIDATION_ACTIVITY_THRESHOLD", "300"))
last_activity = 0
last_action = ""
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
                            last_action = evt.get("action", "")
                except Exception:
                    continue
    except Exception:
        pass
if last_activity > 0:
    age = now - last_activity
    if age > threshold:
        print(f"activity=stale [{age}s old, threshold {threshold}s, last={last_action}]")
    else:
        print(f"activity=ok [{age}s old, last={last_action}]")
else:
    print("activity=missing [no activity log]")
PY
}

cos_validation_lock_message() {
  local project_dir="${1:-${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}}"
  local lock_file="$project_dir/.cognitive-os/runtime/validation-capsule.lock"
  if [ -f "$lock_file" ] && command -v python3 >/dev/null 2>&1; then
    python3 - "$lock_file" <<'PY'
import json, sys
from pathlib import Path
try:
    data = json.loads(Path(sys.argv[1]).read_text())
except Exception:
    data = {}
print(data.get("message") or data.get("command") or "validation capsule active")
PY
  else
    echo "validation capsule active"
  fi
}
