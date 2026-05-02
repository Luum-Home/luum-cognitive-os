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
import signal
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

stale = False
if expires_at and expires_at < now:
    stale = True
elif pid > 0:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        stale = True
    except PermissionError:
        stale = False

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
