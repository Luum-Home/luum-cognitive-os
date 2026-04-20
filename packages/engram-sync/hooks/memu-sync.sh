#!/usr/bin/env bash
# SCOPE: os-only
# memu-sync.sh — Sync session context to memU proactive memory
# Trigger: Stop (after conversation-capture.sh, before session-knowledge-extractor.sh)
# Only runs if memU is available

_HOOK_NAME="memu-sync"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
MEMU_URL="${COGNITIVE_OS_MEMU_URL:-http://localhost:8765}"
METRICS_DIR="$(_resolve_metrics_dir)"

# Check if memU is available
if ! curl -s --connect-timeout 2 "$MEMU_URL/health" >/dev/null 2>&1; then
  exit 0  # memU not running, skip silently
fi

SESSION_ID="${COGNITIVE_OS_SESSION_ID:-unknown}"

# Gather session context for memU's 3-layer memory
# Layer 1 (Resource): raw session data
# Layer 2 (Item): extracted facts/patterns
# Layer 3 (Category): auto-organized by memU

# Push error patterns as "items" (Layer 2)
if [ -f "$METRICS_DIR/error-learning.jsonl" ]; then
  while IFS= read -r line; do
    ERROR_TYPE=$(echo "$line" | jq -r '.type // "unknown"' 2>/dev/null)
    SERVICE=$(echo "$line" | jq -r '.service // "unknown"' 2>/dev/null)
    ERROR_MSG=$(echo "$line" | jq -r '.error // ""' 2>/dev/null | head -c 200)

    PAYLOAD=$(jq -cn \
      --arg type "error_pattern" \
      --arg sid "$SESSION_ID" \
      --arg et "$ERROR_TYPE" \
      --arg svc "$SERVICE" \
      --arg msg "$ERROR_MSG" \
      '{category: "cognitive-os/errors", content: ("\($et) in \($svc): \($msg)"), metadata: {session: $sid, error_type: $et, service: $svc}}')

    curl -s -X POST "$MEMU_URL/api/items" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" \
      --connect-timeout 2 --max-time 5 >/dev/null 2>&1 || true
  done < "$METRICS_DIR/error-learning.jsonl"
fi

# Push repair outcomes as "items"
if [ -f "$METRICS_DIR/repair-outcomes.jsonl" ]; then
  REPAIRS_OK=$(grep -c '"success"' "$METRICS_DIR/repair-outcomes.jsonl" 2>/dev/null || echo 0)
  REPAIRS_FAIL=$(grep -c '"failure"' "$METRICS_DIR/repair-outcomes.jsonl" 2>/dev/null || echo 0)

  PAYLOAD=$(jq -cn \
    --arg sid "$SESSION_ID" \
    --argjson ok "$REPAIRS_OK" \
    --argjson fail "$REPAIRS_FAIL" \
    '{category: "cognitive-os/repairs", content: "Session \($sid): \($ok) successful repairs, \($fail) failed", metadata: {session: $sid, repairs_ok: $ok, repairs_failed: $fail}}')

  curl -s -X POST "$MEMU_URL/api/items" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    --connect-timeout 2 --max-time 5 >/dev/null 2>&1 || true
fi

exit 0
