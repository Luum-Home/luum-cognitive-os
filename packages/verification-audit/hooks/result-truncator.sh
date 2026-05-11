#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: performance, quality, observability
# Hook: Result Truncator — PostToolUse for Bash
# Prevents large tool outputs from flooding the context window.
# Reads the tool result JSON from stdin, truncates tool_response if too long,
# and outputs the modified JSON. Preserves the JSON structure.
#
# Configuration from cognitive-os.yaml:
#   tokens.result_truncation.enabled: true
#   tokens.result_truncation.max_chars: 5000
#   tokens.result_truncation.head_chars: 2000
#   tokens.result_truncation.tail_chars: 1000
#   tokens.result_truncation.never_truncate_patterns: ["FAIL", "ERROR", ...]

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="result-truncator"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

PROJECT_DIR="$_PROJECT_DIR"
COGNITIVE_OS_DIR="$PROJECT_DIR/.cognitive-os"
CONFIG="$_CONFIG_FILE"
METRICS_DIR="$(resolve_session_dir)"
METRICS_FILE="$METRICS_DIR/truncation-events.jsonl"

# Read tool result from stdin (cached via common.sh)
read_stdin_json
INPUT="$_STDIN_JSON"

# --- Load configuration ---
# Defaults
MAX_CHARS=5000
HEAD_CHARS=2000
TAIL_CHARS=1000
ENABLED="true"
PATTERNS=""

if [ -f "$CONFIG" ]; then
  # Check if truncation is enabled
  ENABLED_VAL=$(grep -A1 "result_truncation:" "$CONFIG" 2>/dev/null | grep "enabled:" | awk '{print $2}' || echo "true")
  [ -n "$ENABLED_VAL" ] && ENABLED="$ENABLED_VAL"

  # Read char limits
  MAX_VAL=$(grep -A10 "result_truncation:" "$CONFIG" 2>/dev/null | grep "max_chars:" | awk '{print $2}' || true)
  HEAD_VAL=$(grep -A10 "result_truncation:" "$CONFIG" 2>/dev/null | grep "head_chars:" | awk '{print $2}' || true)
  TAIL_VAL=$(grep -A10 "result_truncation:" "$CONFIG" 2>/dev/null | grep "tail_chars:" | awk '{print $2}' || true)

  [ -n "$MAX_VAL" ] && [[ "$MAX_VAL" =~ ^[0-9]+$ ]] && MAX_CHARS="$MAX_VAL"
  [ -n "$HEAD_VAL" ] && [[ "$HEAD_VAL" =~ ^[0-9]+$ ]] && HEAD_CHARS="$HEAD_VAL"
  [ -n "$TAIL_VAL" ] && [[ "$TAIL_VAL" =~ ^[0-9]+$ ]] && TAIL_CHARS="$TAIL_VAL"

  # Read never_truncate_patterns from YAML (lines starting with - under never_truncate_patterns)
  PATTERNS=$(awk '/never_truncate_patterns:/,/^[^ ]/{if(/^ *- /) print}' "$CONFIG" 2>/dev/null | sed 's/^ *- *//;s/"//g;s/'"'"'//g' || true)
fi

# If disabled, pass through unchanged
if [ "$ENABLED" != "true" ]; then
  echo "$INPUT"
  exit 0
fi

# --- Extract tool_response ---
RESPONSE=$(echo "$INPUT" | jq -r '.tool_response // empty' 2>/dev/null)

# No response or empty — pass through
if [ -z "$RESPONSE" ]; then
  echo "$INPUT"
  exit 0
fi

# --- Check length ---
RESPONSE_LEN=${#RESPONSE}

if [ "$RESPONSE_LEN" -le "$MAX_CHARS" ]; then
  # Under threshold — pass through unchanged
  echo "$INPUT"
  exit 0
fi

# --- ADR-263: Tool-Replay Budget Ledger lookup ---
# Consult the per-session ledger before truncating.
# Modes: fresh → apply smart_truncator fallback (current behaviour)
#        preview → apply catalog thresholds for this tool
#        reference_only → replace with [REF:...] pointer + write spillover
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // "Bash"' 2>/dev/null || echo "Bash")
TOOL_ARGS=$(echo "$INPUT" | jq -r '.tool_input | tostring' 2>/dev/null | head -c 500 || echo "")

LEDGER_ENABLED=$(grep -A3 "tool_replay_ledger:" "$CONFIG" 2>/dev/null | grep "enabled:" | awk '{print $2}' || echo "true")

if [ "${LEDGER_ENABLED:-true}" = "true" ]; then
  export _LEDGER_TOOL_NAME="$TOOL_NAME"
  export _LEDGER_TOOL_ARGS="$TOOL_ARGS"
  export _LEDGER_RESULT_CHARS="$RESPONSE_LEN"
  export _LEDGER_SESSION_ID="${CLAUDE_SESSION_ID:-}"
  export _LEDGER_LIB="$PROJECT_DIR/lib"
  export _LEDGER_PROJECT_DIR="$PROJECT_DIR"

  LEDGER_RESULT=$(python3 -c '
import sys, os
sys.path.insert(0, os.environ["_LEDGER_LIB"])
try:
    from tool_replay_ledger import ToolReplayLedger, compute_target_hash, Mode
    session_id = os.environ.get("_LEDGER_SESSION_ID") or None
    tool_name  = os.environ.get("_LEDGER_TOOL_NAME", "Bash")
    tool_args  = os.environ.get("_LEDGER_TOOL_ARGS", "")
    result_chars = int(os.environ.get("_LEDGER_RESULT_CHARS", "0"))
    project_dir  = os.environ.get("_LEDGER_PROJECT_DIR", ".")
    os.environ["PROJECT_DIR"] = project_dir

    target_hash = compute_target_hash(tool_args)
    ledger = ToolReplayLedger(session_id=session_id)
    decision = ledger.record(tool_name, target_hash, result_chars)
    # Output: "mode|target_hash|session_dir"
    print(f"{decision.mode.value}|{target_hash}|{ledger._session_id}")
except Exception as e:
    # Graceful degradation: fall through to existing behaviour
    print("fresh|unknown|default")
' 2>/dev/null)

  LEDGER_MODE=$(echo "$LEDGER_RESULT" | cut -d'|' -f1)
  LEDGER_TARGET_HASH=$(echo "$LEDGER_RESULT" | cut -d'|' -f2)
  LEDGER_SESSION_ID_RESOLVED=$(echo "$LEDGER_RESULT" | cut -d'|' -f3)

  case "${LEDGER_MODE:-fresh}" in
    reference_only)
      # Write spillover and replace output with [REF:...] pointer
      SPILLOVER_RESULT=$(export _REF_TOOL="$TOOL_NAME"; \
        export _REF_HASH="$LEDGER_TARGET_HASH"; \
        export _REF_SID="$LEDGER_SESSION_ID_RESOLVED"; \
        export _REF_CONTENT="$RESPONSE"; \
        export _LEDGER_LIB="$PROJECT_DIR/lib"; \
        export _LEDGER_PROJECT_DIR="$PROJECT_DIR"; \
        python3 -c '
import sys, os
sys.path.insert(0, os.environ["_LEDGER_LIB"])
try:
    from tool_replay_ledger import ToolReplayLedger
    session_id   = os.environ.get("_REF_SID")
    tool_name    = os.environ.get("_REF_TOOL", "Bash")
    target_hash  = os.environ.get("_REF_HASH", "unknown")
    content      = os.environ.get("_REF_CONTENT", "")
    os.environ["PROJECT_DIR"] = os.environ.get("_LEDGER_PROJECT_DIR", ".")
    ledger = ToolReplayLedger(session_id=session_id)
    spill_path = ledger.write_spillover(tool_name, target_hash, content)
    pointer    = ledger.make_pointer(tool_name, target_hash, spill_path)
    print(pointer)
except Exception as e:
    print("")
' 2>/dev/null)

      if [ -n "$SPILLOVER_RESULT" ]; then
        RESULT=$(echo "$INPUT" | jq --arg tr "$SPILLOVER_RESULT" '.tool_response = $tr' 2>/dev/null)
        if [ $? -eq 0 ] && [ -n "$RESULT" ]; then
          echo "$RESULT"
          TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
          ENTRY="{\"timestamp\":\"${TIMESTAMP}\",\"original_chars\":${RESPONSE_LEN},\"truncated_chars\":${#SPILLOVER_RESULT},\"method\":\"reference_only\",\"tool\":\"${TOOL_NAME}\"}"
          safe_jsonl_append "$METRICS_FILE" "$ENTRY"
          exit 0
        fi
      fi
      # Fall through to smart_truncator if spillover write failed
      ;;

    preview)
      # Apply catalog thresholds for this tool
      PREVIEW_RESULT=$(export _PREV_TOOL="$TOOL_NAME"; \
        export _PREV_CONTENT="$RESPONSE"; \
        export _LEDGER_LIB="$PROJECT_DIR/lib"; \
        python3 -c '
import sys, os
sys.path.insert(0, os.environ["_LEDGER_LIB"])
try:
    from tool_budget_catalog import get_entry
    tool_name = os.environ.get("_PREV_TOOL", "Bash")
    content   = os.environ.get("_PREV_CONTENT", "")
    entry     = get_entry(tool_name)
    # Only truncate if content exceeds trim_threshold (hysteresis)
    if len(content) <= entry.trim_threshold_chars:
        print(content, end="")
    else:
        limit = entry.preview_max_chars
        head  = content[:limit // 2]
        tail  = content[-(limit // 2):]
        msg   = f"\n... [PREVIEW: {len(content)} chars, showing {limit//2}+{limit//2}] ...\n"
        print(head + msg + tail, end="")
except Exception:
    print("")
' 2>/dev/null)

      if [ -n "$PREVIEW_RESULT" ] && [ "${#PREVIEW_RESULT}" -lt "$RESPONSE_LEN" ]; then
        RESULT=$(echo "$INPUT" | jq --arg tr "$PREVIEW_RESULT" '.tool_response = $tr' 2>/dev/null)
        if [ $? -eq 0 ] && [ -n "$RESULT" ]; then
          echo "$RESULT"
          TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
          ENTRY="{\"timestamp\":\"${TIMESTAMP}\",\"original_chars\":${RESPONSE_LEN},\"truncated_chars\":${#PREVIEW_RESULT},\"method\":\"preview\",\"tool\":\"${TOOL_NAME}\"}"
          safe_jsonl_append "$METRICS_FILE" "$ENTRY"
          exit 0
        fi
      fi
      # Fall through to smart_truncator if preview produced no reduction
      ;;

    fresh|*)
      # FRESH: fall through to existing smart_truncator behaviour below
      ;;
  esac
fi
# --- End ADR-263 ledger lookup ---

# --- Check never_truncate_patterns ---
# If the response contains critical patterns, do NOT truncate
if [ -n "$PATTERNS" ]; then
  SKIP_TRUNCATION=false
  while IFS= read -r pattern; do
    [ -z "$pattern" ] && continue
    if echo "$RESPONSE" | grep -qF "$pattern"; then
      # Pattern found — check if this is a summary section (last 2000 chars)
      # containing the pattern. If the whole output is huge but the important
      # content is in the tail, we still want to keep it.
      # Strategy: if pattern appears in both head and tail, skip truncation entirely.
      # If pattern only in tail, the tail will be preserved by truncation anyway.
      HEAD_CHECK=$(echo "$RESPONSE" | head -c "$HEAD_CHARS")
      TAIL_CHECK=$(echo "$RESPONSE" | tail -c "$TAIL_CHARS")
      if echo "$HEAD_CHECK" | grep -qF "$pattern" || echo "$TAIL_CHECK" | grep -qF "$pattern"; then
        # Pattern is in the preserved sections — truncation is safe
        continue
      else
        # Pattern only in middle — skip truncation to preserve it
        SKIP_TRUNCATION=true
        break
      fi
    fi
  done <<< "$PATTERNS"

  if [ "$SKIP_TRUNCATION" = true ]; then
    echo "$INPUT"
    exit 0
  fi
fi

# --- Try smart truncation first ---
# Command-type-aware structured extraction (Workstream 3: intelligent-context-compaction)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // "unknown"' 2>/dev/null | head -c 500)
export _SMART_TRUNC_CMD="$COMMAND"
export _SMART_TRUNC_MAX="$MAX_CHARS"
export _SMART_TRUNC_LIB="$PROJECT_DIR/lib"

SMART_RESULT=$(printf '%s' "$RESPONSE" | python3 -c '
import sys
import os
sys.path.insert(0, os.environ.get("_SMART_TRUNC_LIB", ""))
try:
    from smart_truncator import smart_truncate
    output = sys.stdin.read()
    cmd = os.environ.get("_SMART_TRUNC_CMD", "unknown")
    max_chars = int(os.environ.get("_SMART_TRUNC_MAX", "5000"))
    result = smart_truncate(cmd, output, max_chars)
    # Only emit if we produced a structured summary shorter than the original
    if result and len(result) < len(output):
        print(result, end="")
except Exception:
    pass  # Fall through to head+tail
' 2>/dev/null)

if [ -n "$SMART_RESULT" ]; then
  # Use smart structured extraction result
  RESULT=$(echo "$INPUT" | jq --arg tr "$SMART_RESULT" '.tool_response = $tr' 2>/dev/null)
  if [ $? -eq 0 ] && [ -n "$RESULT" ]; then
    echo "$RESULT"

    # Log smart truncation event
    mkdir -p "$METRICS_DIR"
    COMMAND_ESCAPED=$(echo "$COMMAND" | jq -Rs '.' 2>/dev/null || echo '"unknown"')
    TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    ENTRY="{\"timestamp\":\"${TIMESTAMP}\",\"original_chars\":${RESPONSE_LEN},\"truncated_chars\":${#SMART_RESULT},\"method\":\"smart\",\"command\":${COMMAND_ESCAPED}}"
    safe_jsonl_append "$METRICS_FILE" "$ENTRY"
    exit 0
  fi
fi

# --- Truncate (head+tail fallback) ---
HEAD_PART=$(echo "$RESPONSE" | head -c "$HEAD_CHARS")
TAIL_PART=$(echo "$RESPONSE" | tail -c "$TAIL_CHARS")
TRUNCATION_MSG="\n... [TRUNCATED: ${RESPONSE_LEN} chars total, showing first ${HEAD_CHARS} + last ${TAIL_CHARS}] ...\n"

TRUNCATED_RESPONSE="${HEAD_PART}${TRUNCATION_MSG}${TAIL_PART}"

# --- Rebuild JSON with truncated response ---
# Use jq to safely replace the tool_response field while preserving all other fields
RESULT=$(echo "$INPUT" | jq --arg tr "$TRUNCATED_RESPONSE" '.tool_response = $tr' 2>/dev/null)

if [ $? -eq 0 ] && [ -n "$RESULT" ]; then
  echo "$RESULT"
else
  # If jq fails for any reason, output original to avoid breaking the protocol
  echo "$INPUT"
  exit 0
fi

# --- Log truncation event ---
mkdir -p "$METRICS_DIR"

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // "unknown"' 2>/dev/null | head -c 200)
COMMAND_ESCAPED=$(echo "$COMMAND" | jq -Rs '.' 2>/dev/null || echo '"unknown"')
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

ENTRY="{\"timestamp\":\"${TIMESTAMP}\",\"original_chars\":${RESPONSE_LEN},\"truncated_chars\":${#TRUNCATED_RESPONSE},\"head_chars\":${HEAD_CHARS},\"tail_chars\":${TAIL_CHARS},\"command\":${COMMAND_ESCAPED}}"
safe_jsonl_append "$METRICS_FILE" "$ENTRY"

exit 0
