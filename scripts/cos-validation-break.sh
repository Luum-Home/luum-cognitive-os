#!/usr/bin/env bash
# SCOPE: os-only
# cos-validation-break.sh — targeted, audited recovery for a stale validation lock.
#
# Per ADR-113 P4. Replaces the global COS_VALIDATION_ALLOW_CONCURRENT_AGENTS=1
# bypass with a focused operation that:
#   1. Verifies the --capsule ID matches the active lock (prevents typo break)
#   2. SIGTERM the PID, wait, SIGKILL if still alive (unless --no-kill)
#   3. Removes the lock file
#   4. Removes the worktree at capsule_dir
#   5. Appends an audit entry to .cognitive-os/audit/validation-breaks.jsonl
#
# Exit codes: 0 success, 1 mismatch / not stale, 2 invalid args / no lock

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$("$SCRIPT_DIR/cos-root" project)"
LOCK_FILE="$PROJECT_DIR/.cognitive-os/runtime/validation-capsule.lock"
AUDIT_DIR="$PROJECT_DIR/.cognitive-os/audit"
AUDIT_FILE="$AUDIT_DIR/validation-breaks.jsonl"

CAPSULE=""
REASON=""
FORCE=0
NO_KILL=0

usage() {
  cat <<EOF
Usage: cos validation break --capsule <run_id> --reason <text> [--force] [--no-kill]

Break a stale validation capsule lock.

  --capsule ID  Required. Must match the active lock's run_id.
  --reason TEXT Required. Audit trail explanation.
  --force       Skip confirmation prompt.
  --no-kill     Remove the lock and worktree without signaling the PID.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --capsule) CAPSULE="${2:-}"; shift 2 ;;
    --capsule=*) CAPSULE="${1#--capsule=}"; shift ;;
    --reason) REASON="${2:-}"; shift 2 ;;
    --reason=*) REASON="${1#--reason=}"; shift ;;
    --force) FORCE=1; shift ;;
    --no-kill) NO_KILL=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

[ -n "$CAPSULE" ] || { echo "Error: --capsule required" >&2; usage; exit 2; }
[ -n "$REASON" ] || { echo "Error: --reason required (audit trail)" >&2; usage; exit 2; }

if [ ! -f "$LOCK_FILE" ]; then
  echo "No lock at $LOCK_FILE — nothing to break."
  exit 0
fi

command -v python3 >/dev/null 2>&1 || { echo "python3 required" >&2; exit 2; }

# Read lock data
LOCK_RUN_ID=$(python3 -c "
import json,sys
from pathlib import Path
try:
    print(json.loads(Path('$LOCK_FILE').read_text()).get('run_id',''))
except Exception:
    print('')
")
LOCK_PID=$(python3 -c "
import json,sys
from pathlib import Path
try:
    print(json.loads(Path('$LOCK_FILE').read_text()).get('pid',0))
except Exception:
    print(0)
")
LOCK_CAPSULE_DIR=$(python3 -c "
import json,sys
from pathlib import Path
try:
    print(json.loads(Path('$LOCK_FILE').read_text()).get('capsule_dir',''))
except Exception:
    print('')
")

if [ "$LOCK_RUN_ID" != "$CAPSULE" ]; then
  echo "Error: --capsule '$CAPSULE' does not match active lock run_id '$LOCK_RUN_ID'." >&2
  echo "       Run \`bash scripts/cos-validation-status.sh\` to see active lock." >&2
  exit 1
fi

# Get staleness signals
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/../hooks/_lib/validation-lock.sh"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/../hooks/_lib/safe-worktree-remove.sh"
SIGNALS=$(cos_validation_lock_stale_reason "$PROJECT_DIR")
STALE_LIST=$(echo "$SIGNALS" | grep '=stale' | sed 's/=.*//' | tr '\n' ',' | sed 's/,$//')

# Confirmation
if [ "$FORCE" != "1" ]; then
  echo "About to break validation capsule:"
  echo "  run_id:      $LOCK_RUN_ID"
  echo "  pid:         $LOCK_PID"
  echo "  capsule_dir: $LOCK_CAPSULE_DIR"
  echo "  reason:      $REASON"
  echo "  stale signals: ${STALE_LIST:-none (forcing break)}"
  echo ""
  if [ "$NO_KILL" = "1" ]; then
    echo "Will: remove lock, remove worktree (NOT killing PID)."
  else
    echo "Will: SIGTERM PID, wait 5s, SIGKILL if still alive, remove lock, remove worktree."
  fi
  echo -n "Continue? [y/N] "
  read -r ans
  case "$ans" in
    y|Y|yes|YES) ;;
    *) echo "Aborted."; exit 0 ;;
  esac
fi

# Kill PID
if [ "$NO_KILL" != "1" ] && [ "$LOCK_PID" != "0" ]; then
  if kill -0 "$LOCK_PID" 2>/dev/null; then
    kill -TERM "$LOCK_PID" 2>/dev/null || true
    sleep 5
    if kill -0 "$LOCK_PID" 2>/dev/null; then
      kill -KILL "$LOCK_PID" 2>/dev/null || true
    fi
    KILL_METHOD="sigterm-then-sigkill"
  else
    KILL_METHOD="pid-already-dead"
  fi
else
  KILL_METHOD="no-kill"
fi

# Remove lock
rm -f "$LOCK_FILE"

# Remove worktree
if [ -n "$LOCK_CAPSULE_DIR" ] && [ -d "$LOCK_CAPSULE_DIR" ]; then
  safe_worktree_remove "$PROJECT_DIR" "$LOCK_CAPSULE_DIR" "cos-validation-break"
fi

# Audit
mkdir -p "$AUDIT_DIR"
python3 - "$AUDIT_FILE" "$LOCK_RUN_ID" "$LOCK_PID" "$REASON" "$STALE_LIST" "$KILL_METHOD" <<'PY'
import json, os, sys, time
from pathlib import Path
audit_file, run_id, pid, reason, stale_list, method = sys.argv[1:]
entry = {
    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "actor_pid": os.getppid(),
    "broken_capsule": run_id,
    "broken_pid": int(pid),
    "reason": reason,
    "stale_signals": [s for s in stale_list.split(",") if s],
    "method": method,
}
with Path(audit_file).open("a") as f:
    f.write(json.dumps(entry, separators=(",", ":")) + "\n")
PY

echo "Lock broken. Audit: $AUDIT_FILE"
exit 0
