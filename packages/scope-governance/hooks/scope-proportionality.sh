#!/usr/bin/env bash
# PostToolUse hook: Scope Proportionality Check
# Fires on "Agent" tool use — checks if response is proportional to the task.
# CONCERNS: safety, proportionality, governance
#
# PURPOSE: Prevents "fix bug" from becoming "rewrite system."
# A well-known failure mode in AI coding agents is disproportionate response:
# a simple fix task triggers sweeping deletions or rewrites that far exceed
# the original scope. This hook detects and warns about such disproportion.
#
# Rules:
#   1. Fix tasks should NOT delete files (BLOCK in production, WARN in reconstruction)
#   2. Fix tasks touching >20 files is disproportionate (WARN)
#   3. Any task deleting >5 files needs justification (WARN)

set -uo pipefail

source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 5
check_capability_level "scope-proportionality"

check_private_mode

# Only process Agent tool
read_stdin_json
TOOL_NAME=$(echo "$_STDIN_JSON" | jq -r '.tool_name // ""' 2>/dev/null)
[ "$TOOL_NAME" != "Agent" ] && exit 0

RESPONSE=$(echo "$_STDIN_JSON" | jq -r '.tool_response // ""' 2>/dev/null)
TASK_DESC=$(echo "$_STDIN_JSON" | jq -r '.tool_input.prompt // .tool_input.description // ""' 2>/dev/null | head -c 500)

# Exit early if no meaningful data
[ -z "$RESPONSE" ] && exit 0
[ -z "$TASK_DESC" ] && exit 0

# Detect task type from description
TASK_TYPE="unknown"
if echo "$TASK_DESC" | grep -qiE 'fix|bug|patch|hotfix|typo|correction'; then
    TASK_TYPE="fix"
elif echo "$TASK_DESC" | grep -qiE 'refactor|rewrite|rebuild|migrate'; then
    TASK_TYPE="refactor"
elif echo "$TASK_DESC" | grep -qiE 'add|create|implement|new|feature'; then
    TASK_TYPE="feature"
fi

# Count files mentioned in response
FILES_CREATED=$(echo "$RESPONSE" | grep -ciE 'created|new file|write.*file' || true)
FILES_MODIFIED=$(echo "$RESPONSE" | grep -ciE 'modified|edited|updated|changed' || true)
FILES_DELETED=$(echo "$RESPONSE" | grep -ciE 'deleted|removed|rm |unlink' || true)
TOTAL_FILES=$((FILES_CREATED + FILES_MODIFIED + FILES_DELETED))

# Get current phase for phase-aware behavior
PHASE=$(get_phase "reconstruction")

# Metrics logging
METRICS_DIR=$(resolve_session_dir)
LOG_FILE="$METRICS_DIR/scope-proportionality.jsonl"
mkdir -p "$METRICS_DIR" 2>/dev/null

log_event() {
    local severity="$1"
    local message="$2"
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")
    printf '{"timestamp":"%s","task_type":"%s","severity":"%s","files_created":%d,"files_modified":%d,"files_deleted":%d,"total_files":%d,"phase":"%s","message":"%s","task":"%s"}\n' \
        "$ts" "$TASK_TYPE" "$severity" "$FILES_CREATED" "$FILES_MODIFIED" "$FILES_DELETED" "$TOTAL_FILES" "$PHASE" "$message" \
        "$(echo "$TASK_DESC" | head -c 100 | tr '"' "'")" \
        >> "$LOG_FILE" 2>/dev/null
}

# RULE 1: Fix tasks should NOT delete files
if [ "$TASK_TYPE" = "fix" ] && [ "$FILES_DELETED" -gt 0 ]; then
    if [ "$PHASE" = "production" ] || [ "$PHASE" = "maintenance" ]; then
        echo "SCOPE PROPORTIONALITY: BLOCK" >&2
        echo "Task type 'fix' but agent DELETED $FILES_DELETED file(s)." >&2
        echo "A fix should patch, not delete. Review the agent's approach." >&2
        echo "Phase '$PHASE' enforces strict proportionality for fix tasks." >&2
        log_event "BLOCK" "Fix task deleted files in $PHASE phase"
        exit 2  # BLOCK
    else
        echo "SCOPE PROPORTIONALITY: WARNING" >&2
        echo "Task type 'fix' but agent DELETED $FILES_DELETED file(s)." >&2
        echo "A fix should patch, not delete. Review the agent's approach." >&2
        log_event "WARN" "Fix task deleted files in $PHASE phase"
    fi
fi

# RULE 2: Fix tasks touching >20 files is disproportionate
if [ "$TASK_TYPE" = "fix" ] && [ "$TOTAL_FILES" -gt 20 ]; then
    echo "SCOPE PROPORTIONALITY: WARNING" >&2
    echo "Task type 'fix' but agent touched $TOTAL_FILES files." >&2
    echo "This seems disproportionate for a bug fix." >&2
    log_event "WARN" "Fix task touched $TOTAL_FILES files"
fi

# RULE 3: Any task deleting >5 files needs justification
if [ "$FILES_DELETED" -gt 5 ]; then
    echo "SCOPE PROPORTIONALITY: WARNING" >&2
    echo "Agent deleted $FILES_DELETED files. Verify this is intentional." >&2
    log_event "WARN" "Agent deleted $FILES_DELETED files"
fi

exit 0
