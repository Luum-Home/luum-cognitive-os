#!/usr/bin/env bash
# SCOPE: os-only
# cos-validation-status.sh — diagnose the active validation capsule lock.
#
# Per ADR-113 P3. Reports per-signal liveness (TTL, PID, heartbeat, activity)
# and an overall verdict: HEALTHY / STALE / NO_LOCK.
#
# Exit codes:
#   0 = healthy or no lock
#   1 = stale (operator should consider `cos validation break`)
#   2 = lock exists but cannot be diagnosed (corrupt / no python3)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$("$SCRIPT_DIR/cos-root" project)"
LOCK_FILE="$PROJECT_DIR/.cognitive-os/runtime/validation-capsule.lock"

JSON=0
while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON=1; shift ;;
    --help|-h) cat <<EOF
Usage: cos validation status [--json]

Diagnose the active validation capsule lock.
EOF
      exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ ! -f "$LOCK_FILE" ]; then
  if [ "$JSON" = "1" ]; then
    echo '{"verdict":"NO_LOCK","lock_file":"'"$LOCK_FILE"'"}'
  else
    echo "No validation capsule lock present."
    echo "Lock path: $LOCK_FILE"
  fi
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not available; cannot diagnose lock." >&2
  exit 2
fi

# Read lock contents
LOCK_DATA=$(python3 -c "
import json, sys
from pathlib import Path
try:
    print(json.dumps(json.loads(Path('$LOCK_FILE').read_text())))
except Exception as e:
    print(json.dumps({'_error': str(e)}))
")

# Get staleness signals via library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB="$SCRIPT_DIR/../hooks/_lib/validation-lock.sh"
# shellcheck source=/dev/null
source "$LIB"
SIGNALS=$(cos_validation_lock_stale_reason "$PROJECT_DIR")

# Compute verdict: HEALTHY if all known signals are ok, STALE if any stale
VERDICT="HEALTHY"
while IFS= read -r line; do
  case "$line" in
    *=stale*) VERDICT="STALE" ;;
  esac
done <<< "$SIGNALS"

# Output
if [ "$JSON" = "1" ]; then
  python3 - "$LOCK_DATA" "$SIGNALS" "$VERDICT" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
signals_raw = sys.argv[2].strip().split("\n")
verdict = sys.argv[3]
signals = {}
for line in signals_raw:
    if "=" in line:
        k, v = line.split("=", 1)
        signals[k] = v
print(json.dumps({
    "verdict": verdict,
    "lock": data,
    "signals": signals,
}, separators=(",", ":")))
PY
else
  RUN_ID=$(echo "$LOCK_DATA" | python3 -c "import json,sys;print(json.load(sys.stdin).get('run_id','?'))")
  PID=$(echo "$LOCK_DATA" | python3 -c "import json,sys;print(json.load(sys.stdin).get('pid','?'))")
  STARTED=$(echo "$LOCK_DATA" | python3 -c "
import json,sys,time
d=json.load(sys.stdin)
ts=d.get('started_at_epoch',0)
if ts:
    age=int(time.time())-int(ts)
    h,r=divmod(age,3600); m,s=divmod(r,60)
    print(f'{h}h {m}m {s}s ago' if h else f'{m}m {s}s ago' if m else f'{s}s ago')
else:
    print('unknown')
")
  CAPSULE_DIR=$(echo "$LOCK_DATA" | python3 -c "import json,sys;print(json.load(sys.stdin).get('capsule_dir','?'))")

  echo "Capsule:        $RUN_ID"
  echo "PID:            $PID"
  echo "Started:        $STARTED"
  echo "Capsule dir:    $CAPSULE_DIR"
  echo ""
  echo "Signals:"
  echo "$SIGNALS" | sed 's/^/  /'
  echo ""
  echo "Verdict:        $VERDICT"
  if [ "$VERDICT" = "STALE" ]; then
    echo ""
    echo "Suggestion:     bash scripts/cos-validation-break.sh \\"
    echo "                  --capsule $RUN_ID \\"
    echo "                  --reason \"<describe staleness>\""
  fi
fi

[ "$VERDICT" = "STALE" ] && exit 1
exit 0
