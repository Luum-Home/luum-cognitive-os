#!/usr/bin/env bash
# SCOPE: os-only
# benchmark-hooks.sh — Measure real execution time of all registered hooks
#
# PERFORMANCE CONTRACT:
#   This script must run in <60s total.
#   It benchmarks every hook registered in settings.json.
#
# Usage: bash scripts/benchmark-hooks.sh [--warn-ms 500] [--fail-ms 2000]
#
# Output:
#   Per-hook timing with PASS/WARN/FAIL classification
#   Cumulative overhead per event type (SessionStart, PreToolUse, etc.)
#   Total overhead per tool call (PreToolUse + PostToolUse combined)
#
# Exit codes:
#   0 = all hooks under --fail-ms
#   1 = at least one hook exceeds --fail-ms

set -euo pipefail

WARN_MS=500
FAIL_MS=2000

while [ $# -gt 0 ]; do
  case "$1" in
    --warn-ms) WARN_MS="$2"; shift 2 ;;
    --fail-ms) FAIL_MS="$2"; shift 2 ;;
    *) echo "Usage: $0 [--warn-ms N] [--fail-ms N]"; exit 1 ;;
  esac
done

SOURCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_ROOT="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$SOURCE_ROOT}}}"
source "$SOURCE_ROOT/scripts/_lib/settings-driver.sh"
SETTINGS="$(cos_settings_driver_path "$PROJECT_ROOT" "$(cos_detect_harness "$PROJECT_ROOT")")"
SETTINGS_LABEL="$(cos_settings_driver_label "$(cos_detect_harness "$PROJECT_ROOT")")"

if [ ! -f "$SETTINGS" ]; then
  echo "ERROR: No active settings driver found at $SETTINGS_LABEL"
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required"
  exit 1
fi

run_hook_with_timeout() {
  local hook_command="$1"
  if command -v timeout >/dev/null 2>&1; then
    timeout 5 bash -c "$hook_command" </dev/null >/dev/null 2>/dev/null
    return $?
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -c '
import subprocess
import sys

try:
    completed = subprocess.run(
        sys.argv[1],
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
    )
    raise SystemExit(completed.returncode)
except subprocess.TimeoutExpired:
    raise SystemExit(124)
' "$hook_command"
    return $?
  fi
  bash -c "$hook_command" </dev/null >/dev/null 2>/dev/null
}

# Extract all hooks with their event type
HOOKS_JSON=$(jq -r '
  .hooks | to_entries[] | .key as $event |
  .value[].hooks[]? |
  "\($event)\t\(.command)\t\(.async // false)"
' "$SETTINGS" 2>/dev/null)

echo "================================================================"
echo "  Hook Performance Benchmark"
echo "  WARN threshold: ${WARN_MS}ms | FAIL threshold: ${FAIL_MS}ms"
echo "================================================================"
echo ""

TOTAL_HOOKS=0
TOTAL_WARN=0
TOTAL_FAIL=0
HAS_FAILURE=0

# Accumulators per event type
declare -A EVENT_TOTAL_MS 2>/dev/null || true  # bash 3.2 compat handled below
SESSION_START_MS=0
PRE_TOOL_MS=0
POST_TOOL_MS=0
STOP_MS=0
OTHER_MS=0

# Set up environment for hooks
export CODEX_PROJECT_DIR="$PROJECT_ROOT"
export CLAUDE_PROJECT_DIR="$PROJECT_ROOT"
export COGNITIVE_OS_PROJECT_DIR="$PROJECT_ROOT"
export TOOL_NAME="Bash"
export TOOL_INPUT='{"command":"echo benchmark"}'
export SESSION_ID="benchmark-$$"
export RESULT_TEXT="benchmark output"
export EXIT_CODE="0"

while IFS=$'\t' read -r event command is_async; do
  [ -z "$command" ] && continue

  # Extract hook name from command
  hook_name=$(echo "$command" | sed 's|.*hooks/||' | sed 's|"||g' | sed 's|\.sh||')

  # Run with timeout and measure
  start_ns=$(date +%s%N 2>/dev/null || echo "$(date +%s)000000000")
  set +e
  run_hook_with_timeout "$command"
  exit_code=$?
  set -e
  end_ns=$(date +%s%N 2>/dev/null || echo "$(date +%s)000000000")

  # Calculate duration
  if [ ${#start_ns} -gt 10 ]; then
    duration_ms=$(( (end_ns - start_ns) / 1000000 ))
  else
    duration_ms=$(( (end_ns - start_ns) / 1000000 ))
  fi

  # Handle timeout
  [ $exit_code -eq 124 ] && duration_ms=10000

  # Classify
  TOTAL_HOOKS=$((TOTAL_HOOKS + 1))
  if [ "$duration_ms" -ge "$FAIL_MS" ]; then
    status="FAIL"
    TOTAL_FAIL=$((TOTAL_FAIL + 1))
    HAS_FAILURE=1
  elif [ "$duration_ms" -ge "$WARN_MS" ]; then
    status="WARN"
    TOTAL_WARN=$((TOTAL_WARN + 1))
  else
    status="PASS"
  fi

  async_tag=""
  [ "$is_async" = "true" ] && async_tag=" [async]"

  printf "  %-5s %6dms  %-20s %-25s%s\n" "$status" "$duration_ms" "$event" "$hook_name" "$async_tag"

  # Accumulate per event type (only sync hooks matter for blocking)
  if [ "$is_async" != "true" ]; then
    case "$event" in
      SessionStart)  SESSION_START_MS=$((SESSION_START_MS + duration_ms)) ;;
      PreToolUse)    PRE_TOOL_MS=$((PRE_TOOL_MS + duration_ms)) ;;
      PostToolUse)   POST_TOOL_MS=$((POST_TOOL_MS + duration_ms)) ;;
      Stop)          STOP_MS=$((STOP_MS + duration_ms)) ;;
      *)             OTHER_MS=$((OTHER_MS + duration_ms)) ;;
    esac
  fi

done <<< "$HOOKS_JSON"

PER_ACTION_MS=$((PRE_TOOL_MS + POST_TOOL_MS))

echo ""
echo "================================================================"
echo "  Summary"
echo "================================================================"
echo ""
echo "  Hooks tested:     $TOTAL_HOOKS"
echo "  PASS (<${WARN_MS}ms):     $((TOTAL_HOOKS - TOTAL_WARN - TOTAL_FAIL))"
echo "  WARN (${WARN_MS}-${FAIL_MS}ms):  $TOTAL_WARN"
echo "  FAIL (>${FAIL_MS}ms):    $TOTAL_FAIL"
echo ""
echo "  ── Sync overhead by lifecycle event (blocking) ──"
echo ""
echo "  SessionStart:     ${SESSION_START_MS}ms  (once per session)"
echo "  PreToolUse:       ${PRE_TOOL_MS}ms  (every tool call)"
echo "  PostToolUse:      ${POST_TOOL_MS}ms  (every tool call)"
echo "  Stop:             ${STOP_MS}ms  (once per session)"
echo ""
echo "  ── Per tool-call overhead ──"
echo ""
echo "  Total sync blocking per action: ${PER_ACTION_MS}ms"
if [ "$PER_ACTION_MS" -gt 5000 ]; then
  echo "  CRITICAL: >${PER_ACTION_MS}ms overhead per tool call will feel broken"
elif [ "$PER_ACTION_MS" -gt 2000 ]; then
  echo "  WARNING: >${PER_ACTION_MS}ms overhead per tool call is noticeable"
elif [ "$PER_ACTION_MS" -gt 1000 ]; then
  echo "  INFO: ${PER_ACTION_MS}ms overhead per tool call is acceptable"
else
  echo "  OK: ${PER_ACTION_MS}ms overhead per tool call is fast"
fi
echo ""

# Write machine-readable results
RESULTS_FILE="$PROJECT_ROOT/.cognitive-os/metrics/hook-benchmark.json"
mkdir -p "$(dirname "$RESULTS_FILE")" 2>/dev/null
cat > "$RESULTS_FILE" <<EOJSON
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "thresholds": {"warn_ms": $WARN_MS, "fail_ms": $FAIL_MS},
  "total_hooks": $TOTAL_HOOKS,
  "pass": $((TOTAL_HOOKS - TOTAL_WARN - TOTAL_FAIL)),
  "warn": $TOTAL_WARN,
  "fail": $TOTAL_FAIL,
  "sync_overhead_ms": {
    "session_start": $SESSION_START_MS,
    "pre_tool_use": $PRE_TOOL_MS,
    "post_tool_use": $POST_TOOL_MS,
    "stop": $STOP_MS,
    "per_action": $PER_ACTION_MS
  }
}
EOJSON

exit $HAS_FAILURE
