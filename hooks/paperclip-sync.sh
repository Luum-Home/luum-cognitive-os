#!/usr/bin/env bash
# paperclip-sync.sh — Sync Cognitive OS metrics to Paperclip dashboard
# Trigger: Stop (before session-cleanup.sh)

_HOOK_NAME="paperclip-sync"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PAPERCLIP_URL="${COGNITIVE_OS_PAPERCLIP_URL:-http://localhost:3456}"
METRICS_DIR="$(_resolve_metrics_dir)"

# Check if Paperclip is available
if ! curl -s --connect-timeout 2 "$PAPERCLIP_URL/api/health" >/dev/null 2>&1; then
  exit 0  # Paperclip not running, skip silently
fi

# Gather session summary
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-unknown}"
ERRORS=$(wc -l < "$METRICS_DIR/error-learning.jsonl" 2>/dev/null | tr -d ' ' || echo 0)
REPAIRS_OK=$(grep -c '"success"' "$METRICS_DIR/repair-outcomes.jsonl" 2>/dev/null || echo 0)
REPAIRS_FAIL=$(grep -c '"failure"' "$METRICS_DIR/repair-outcomes.jsonl" 2>/dev/null || echo 0)
SKILLS=$(wc -l < "$METRICS_DIR/skill-metrics.jsonl" 2>/dev/null | tr -d ' ' || echo 0)
REGISTRY_SIZE=$(wc -l < "$PROJECT_DIR/.cognitive-os/metrics/remediation-registry.jsonl" 2>/dev/null | tr -d ' ' || echo 0)

# Build payload
PAYLOAD=$(jq -cn \
  --arg sid "$SESSION_ID" \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --argjson errors "$ERRORS" \
  --argjson repairs_ok "$REPAIRS_OK" \
  --argjson repairs_fail "$REPAIRS_FAIL" \
  --argjson skills "$SKILLS" \
  --argjson registry "$REGISTRY_SIZE" \
  '{
    type: "cognitive-os-session",
    session_id: $sid,
    timestamp: $ts,
    metrics: {
      errors_captured: $errors,
      repairs_succeeded: $repairs_ok,
      repairs_failed: $repairs_fail,
      skills_executed: $skills,
      registry_size: $registry
    }
  }')

# Push to Paperclip (fire and forget)
curl -s -X POST "$PAPERCLIP_URL/api/artifacts" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  --connect-timeout 2 \
  --max-time 5 \
  >/dev/null 2>&1 || true

exit 0
