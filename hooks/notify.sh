#!/usr/bin/env bash
# PostToolUse hook: Send notifications for SDD phase completions
# Fires on "Agent" tool use — detects SDD phase results and notifies via lib/notifications.py
# Must complete in <5 seconds

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
LOG_FILE="$METRICS_DIR/notify.log"

mkdir -p "$METRICS_DIR"

# Read stdin (JSON with tool_name, tool_input, tool_response)
INPUT=$(cat)

if [ -z "$INPUT" ]; then
  exit 0
fi

# Require jq
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Only process Agent tool completions
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [ "$TOOL_NAME" != "Agent" ]; then
  exit 0
fi

# Check if notifications are configured (skip early if not)
NOTIFY_PROVIDER="${NOTIFY_PROVIDER:-none}"
if [ "$NOTIFY_PROVIDER" = "none" ] || [ -z "$NOTIFY_PROVIDER" ]; then
  exit 0
fi

# Extract task description and response
TASK_DESC=$(echo "$INPUT" | jq -r '.tool_input.task_description // .tool_input.prompt // empty' 2>/dev/null)
RESPONSE=$(echo "$INPUT" | jq -r '.tool_response // empty' 2>/dev/null)

if [ -z "$TASK_DESC" ] && [ -z "$RESPONSE" ]; then
  exit 0
fi

# Detect SDD phase from task description or response
# Phases: sdd-explore, sdd-propose, sdd-spec, sdd-design, sdd-tasks, sdd-apply, sdd-verify, sdd-archive
PHASE=""
CHANGE=""

# Try to detect phase from task description
for p in sdd-explore sdd-propose sdd-spec sdd-design sdd-tasks sdd-apply sdd-verify sdd-archive; do
  if echo "$TASK_DESC" | grep -qi "$p" 2>/dev/null; then
    PHASE="$p"
    break
  fi
done

# If not found in task, try response
if [ -z "$PHASE" ]; then
  for p in sdd-explore sdd-propose sdd-spec sdd-design sdd-tasks sdd-apply sdd-verify sdd-archive; do
    if echo "$RESPONSE" | head -c 2000 | grep -qi "$p" 2>/dev/null; then
      PHASE="$p"
      break
    fi
  done
fi

# No SDD phase detected — nothing to notify
if [ -z "$PHASE" ]; then
  exit 0
fi

# Try to extract change name from task description
# Look for patterns like: "change: foo-bar", "change-name: foo", or quoted names after phase
CHANGE=$(echo "$TASK_DESC" | grep -oiE '(change[_-]?name?|change)\s*[:=]\s*['\''"]?([a-z0-9-]+)' 2>/dev/null | head -1 | sed 's/.*[:=]\s*['\''"]*//' | sed 's/['\''"]*//' || true)
if [ -z "$CHANGE" ]; then
  CHANGE="unknown"
fi

# Detect success or failure from response
STATUS="complete"
ERROR=""

# Check for failure indicators
if echo "$RESPONSE" | head -c 3000 | grep -qiE '(status:\s*(fail|error)|FAIL|CRITICAL|verdict:\s*FAIL)' 2>/dev/null; then
  STATUS="fail"
  # Extract first error line
  ERROR=$(echo "$RESPONSE" | head -c 3000 | grep -iE '(error|FAIL|CRITICAL)' 2>/dev/null | head -1 | cut -c1-200 || true)
fi

# Find Python interpreter
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    PYTHON="$cmd"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) WARN: No python found, skipping notification" >> "$LOG_FILE"
  exit 0
fi

# Send notification via Python module
NOTIFY_SCRIPT=$(cat <<'PYEOF'
import sys, os, json

# Add project root to path so lib is importable
sys.path.insert(0, os.environ.get("PROJECT_DIR", "."))

try:
    from lib.notifications import notify_phase_complete, notify_phase_fail
except ImportError as e:
    print(f"WARN: Cannot import notifications: {e}", file=sys.stderr)
    sys.exit(0)

phase = os.environ.get("PHASE", "")
change = os.environ.get("CHANGE", "unknown")
status = os.environ.get("STATUS", "complete")
error = os.environ.get("ERROR", "")

if status == "fail":
    notify_phase_fail(change=change, phase=phase, error=error)
else:
    notify_phase_complete(change=change, phase=phase)
PYEOF
)

PROJECT_DIR="$PROJECT_DIR" PHASE="$PHASE" CHANGE="$CHANGE" STATUS="$STATUS" ERROR="$ERROR" \
  $PYTHON -c "$NOTIFY_SCRIPT" 2>/dev/null || true

# Log the notification attempt
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) phase=$PHASE change=$CHANGE status=$STATUS" >> "$LOG_FILE"

exit 0
