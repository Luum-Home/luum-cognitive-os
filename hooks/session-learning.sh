#!/bin/bash
# Session Learning Hook — Stop hook (runs at session end)
# Summarizes what went WRONG this session: failed tasks, failed acceptance criteria,
# iteration counts. Saves structured learnings for cross-session analysis by /self-improve.
# Designed to be fast (<3s) and non-blocking.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="session-learning"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
LEARNINGS_FILE="$METRICS_DIR/session-learnings.jsonl"

# Session-aware
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  _SESSION_FILE="$PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  [ -f "$_SESSION_FILE" ] && SESSION_ID=$(cat "$_SESSION_FILE" 2>/dev/null)
fi
SESSION_METRICS_DIR=""
if [ -n "$SESSION_ID" ]; then
  SESSION_METRICS_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/metrics"
fi

mkdir -p "$METRICS_DIR"

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SESSION_START="${COGNITIVE_OS_SESSION_START:-$TIMESTAMP}"

# --- Count errors this session ---
ERROR_FILE="$METRICS_DIR/error-learning.jsonl"
SESSION_ERRORS=0
ERROR_TYPES=""
ERROR_SERVICES=""

if [ -f "$ERROR_FILE" ]; then
  # Get session start epoch
  START_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$SESSION_START" +%s 2>/dev/null || date -d "$SESSION_START" +%s 2>/dev/null || echo "0")

  if [ "$START_EPOCH" -gt 0 ]; then
    SESSION_ERRORS=$(awk -F'"timestamp_epoch":' '{split($2,a,","); if(a[1]+0 > '"$START_EPOCH"') count++} END{print count+0}' "$ERROR_FILE" 2>/dev/null || echo "0")

    # Extract error types and services for this session
    if [ "$SESSION_ERRORS" -gt 0 ]; then
      ERROR_TYPES=$(awk -F'"timestamp_epoch":' '{split($2,a,","); if(a[1]+0 > '"$START_EPOCH"') print}' "$ERROR_FILE" 2>/dev/null | \
        grep -o '"type":"[^"]*"' | sort | uniq -c | sort -rn | head -5 | \
        awk '{gsub(/"type":"/,"",$2); gsub(/"/,"",$2); printf "%s(%s) ", $2, $1}' 2>/dev/null || echo "")

      ERROR_SERVICES=$(awk -F'"timestamp_epoch":' '{split($2,a,","); if(a[1]+0 > '"$START_EPOCH"') print}' "$ERROR_FILE" 2>/dev/null | \
        grep -o '"service":"[^"]*"' | sort | uniq -c | sort -rn | head -5 | \
        awk '{gsub(/"service":"/,"",$2); gsub(/"/,"",$2); printf "%s(%s) ", $2, $1}' 2>/dev/null || echo "")
    fi
  fi
fi

# --- Count skill executions this session ---
SKILL_FILE="$METRICS_DIR/skill-metrics.jsonl"
SESSION_SKILLS_TOTAL=0
SESSION_SKILLS_SUCCESS=0
SESSION_SKILLS_FAILED=0
FAILED_SKILLS=""

if [ -f "$SKILL_FILE" ]; then
  START_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$SESSION_START" +%s 2>/dev/null || date -d "$SESSION_START" +%s 2>/dev/null || echo "0")

  # Count all entries in this session (by timestamp comparison)
  if [ "$START_EPOCH" -gt 0 ]; then
    # Simple line-based analysis — count success and total
    SESSION_SKILLS_TOTAL=$(awk -v start="$SESSION_START" 'BEGIN{count=0} /"timestamp"/{if($0 > "\"timestamp\":\""start) count++} END{print count}' "$SKILL_FILE" 2>/dev/null || echo "0")
    SESSION_SKILLS_SUCCESS=$(awk -v start="$SESSION_START" '/"success":\s*true|"success": true/{if($0 > "\"timestamp\":\""start) count++} END{print count+0}' "$SKILL_FILE" 2>/dev/null || echo "0")
    SESSION_SKILLS_FAILED=$((SESSION_SKILLS_TOTAL - SESSION_SKILLS_SUCCESS))

    # Extract names of failed skills
    FAILED_SKILLS=$(grep -v '"success":\s*true\|"success": true' "$SKILL_FILE" 2>/dev/null | \
      grep -o '"skill":"[^"]*"' | sort | uniq -c | sort -rn | head -5 | \
      awk '{gsub(/"skill":"/,"",$2); gsub(/"/,"",$2); printf "%s(%s) ", $2, $1}' 2>/dev/null || echo "")
  fi
fi

# --- Count auto-refine iterations this session ---
REFINE_DIR="$METRICS_DIR/auto-refine"
TOTAL_REFINE_ITERATIONS=0
REFINE_SESSIONS=0

if [ -d "$REFINE_DIR" ]; then
  for f in "$REFINE_DIR"/*.jsonl; do
    [ -f "$f" ] || continue
    ITERS=$(wc -l < "$f" 2>/dev/null | tr -d ' ')
    if [ "$ITERS" -gt 0 ]; then
      TOTAL_REFINE_ITERATIONS=$((TOTAL_REFINE_ITERATIONS + ITERS))
      REFINE_SESSIONS=$((REFINE_SESSIONS + 1))
    fi
  done
fi

# --- Calculate session success rate ---
SESSION_SUCCESS_RATE="N/A"
if [ "$SESSION_SKILLS_TOTAL" -gt 0 ]; then
  SESSION_SUCCESS_RATE=$(echo "scale=0; ($SESSION_SKILLS_SUCCESS * 100) / $SESSION_SKILLS_TOTAL" | bc 2>/dev/null || echo "N/A")
fi

# --- Write session learning entry ---
LEARNING_ENTRY=$(cat <<JSONEOF
{"timestamp":"${TIMESTAMP}","session_id":"${SESSION_ID:-unknown}","session_errors":${SESSION_ERRORS},"error_types":"${ERROR_TYPES}","error_services":"${ERROR_SERVICES}","skills_total":${SESSION_SKILLS_TOTAL},"skills_success":${SESSION_SKILLS_SUCCESS},"skills_failed":${SESSION_SKILLS_FAILED},"failed_skills":"${FAILED_SKILLS}","refine_iterations":${TOTAL_REFINE_ITERATIONS},"refine_sessions":${REFINE_SESSIONS},"success_rate":"${SESSION_SUCCESS_RATE}"}
JSONEOF
)

safe_jsonl_append "$LEARNINGS_FILE" "$LEARNING_ENTRY"

# --- Output summary (injected into session context) ---
if [ "$SESSION_ERRORS" -gt 0 ] || [ "$SESSION_SKILLS_FAILED" -gt 0 ]; then
  echo ""
  echo "=== SESSION LEARNING SUMMARY ==="
  echo "Errors this session: $SESSION_ERRORS"
  [ -n "$ERROR_TYPES" ] && echo "  Error types: $ERROR_TYPES"
  [ -n "$ERROR_SERVICES" ] && echo "  Services affected: $ERROR_SERVICES"
  echo "Skills executed: $SESSION_SKILLS_TOTAL (success: $SESSION_SKILLS_SUCCESS, failed: $SESSION_SKILLS_FAILED)"
  [ -n "$FAILED_SKILLS" ] && echo "  Failed skills: $FAILED_SKILLS"
  if [ "$TOTAL_REFINE_ITERATIONS" -gt 0 ]; then
    echo "Auto-refine: $TOTAL_REFINE_ITERATIONS iterations across $REFINE_SESSIONS tasks"
  fi
  echo "Session success rate: ${SESSION_SUCCESS_RATE}%"
  echo "=== END SESSION LEARNING ==="
fi

exit 0
