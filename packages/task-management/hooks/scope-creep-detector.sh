#!/usr/bin/env bash
# PostToolUse hook: Scope Creep Detection
# Fires on Edit|Write — detects when agents edit files outside the approved task scope.
# CONCERNS: safety, scope, governance
#
# PURPOSE: Prevents agents from modifying files unrelated to the current task.
# When an active task defines expectedFiles or scope, edits to files outside
# that scope trigger a warning (reconstruction) or block (production).
#
# Exit codes:
#   0 — within scope or no scope defined
#   2 — BLOCK (out of scope in production/maintenance)

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 5
check_capability_level "scope-creep-detector"

check_private_mode

# Read stdin and gate on Edit|Write
read_stdin_json
TOOL_NAME=$(stdin_field '.tool_name' '')
case "$TOOL_NAME" in
    Edit|Write) ;;
    *) exit 0 ;;
esac

FILE_PATH=$(stdin_field '.tool_input.file_path' '')
[ -z "$FILE_PATH" ] && exit 0

# Find active task with scope
TASKS_FILE="$_PROJECT_DIR/.cognitive-os/tasks/active-tasks.json"
[ ! -f "$TASKS_FILE" ] && exit 0

# Get in_progress task with scope or expectedFiles
ACTIVE_TASK=$(jq -r '
  (.tasks // [])[]
  | select(.status == "in_progress")
  | select(.scope != null or .expectedFiles != null or .expectedOutputs != null)
' "$TASKS_FILE" 2>/dev/null | head -c 5000)

[ -z "$ACTIVE_TASK" ] && exit 0

# Collect approved paths from scope, expectedFiles, and expectedOutputs
APPROVED_PATHS=$(echo "$ACTIVE_TASK" | jq -r '
  ((.scope // []) + (.expectedFiles // []) + (.expectedOutputs // []))[]
' 2>/dev/null)

[ -z "$APPROVED_PATHS" ] && exit 0

# Check if the edited file matches any approved path (prefix or glob)
IN_SCOPE="false"
while IFS= read -r approved; do
    [ -z "$approved" ] && continue
    # Exact match
    if [ "$FILE_PATH" = "$approved" ]; then
        IN_SCOPE="true"
        break
    fi
    # Prefix match (directory scope like "internal/users/")
    if [[ "$FILE_PATH" == "$approved"* ]]; then
        IN_SCOPE="true"
        break
    fi
    # Check if approved path is a prefix of the file (e.g., scope: "src/" matches "src/foo.go")
    if [[ "$FILE_PATH" == *"$approved"* ]]; then
        IN_SCOPE="true"
        break
    fi
done <<< "$APPROVED_PATHS"

[ "$IN_SCOPE" = "true" ] && exit 0

# File is outside scope — determine action based on phase
PHASE=$(get_phase "reconstruction")
TASK_DESC=$(echo "$ACTIVE_TASK" | jq -r '.description // .id // "unknown"' 2>/dev/null | head -c 100)

# Log detection
METRICS_DIR=$(resolve_session_dir)
LOG_FILE="$METRICS_DIR/scope-creep.jsonl"
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")
printf '{"timestamp":"%s","file":"%s","task":"%s","phase":"%s","action":"%s"}\n' \
    "$TS" "$FILE_PATH" "$(echo "$TASK_DESC" | tr '"' "'")" "$PHASE" \
    "$([ "$PHASE" = "production" ] || [ "$PHASE" = "maintenance" ] && echo "block" || echo "warn")" \
    >> "$LOG_FILE" 2>/dev/null

if [ "$PHASE" = "production" ] || [ "$PHASE" = "maintenance" ]; then
    echo "SCOPE CREEP: BLOCK" >&2
    echo "File '$FILE_PATH' is outside the approved task scope." >&2
    echo "Active task: $TASK_DESC" >&2
    echo "Phase '$PHASE' enforces strict scope boundaries." >&2
    exit 2
else
    echo "SCOPE CREEP: WARNING" >&2
    echo "File '$FILE_PATH' is outside the approved task scope." >&2
    echo "Active task: $TASK_DESC" >&2
    exit 0
fi
