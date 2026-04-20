#!/usr/bin/env bash
# tool-discovery-trigger.sh — Check if tool discovery scan is due
# Trigger: SessionStart

_HOOK_NAME="tool-discovery-trigger"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
DISCOVERY_FILE="$PROJECT_DIR/metrics/tool-discovery.jsonl"

LAST_SCAN=0
if [ -f "$DISCOVERY_FILE" ]; then
  LAST_SCAN=$(tail -1 "$DISCOVERY_FILE" 2>/dev/null | jq -r '.timestamp_epoch // 0' 2>/dev/null || echo 0)
fi

NOW=$(date +%s)
DAYS_SINCE=$(( (NOW - LAST_SCAN) / 86400 ))

if [ "$DAYS_SINCE" -ge 7 ] || [ "$LAST_SCAN" -eq 0 ]; then
  echo "[tool-discovery] Scan due (last: ${DAYS_SINCE}d ago). Recommend running /tool-discovery" >&2
fi

exit 0
