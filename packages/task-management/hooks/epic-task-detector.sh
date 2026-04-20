#!/usr/bin/env bash
# PreToolUse hook: Epic Task Detector
# Fires on "Agent" tool use — detects tasks that might affect many files
# Advisory only — does NOT block. Suggests running /sandbox-sample first.
# Must complete in <3 seconds
#
# PURPOSE: Catches large-scope tasks BEFORE they reach agents.
# Without sampling, agents apply changes to hundreds of files blindly,
# breaking documentation, corrupting configs, and reporting "done."

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="epic-task-detector"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 5
check_capability_level "epic-task-detector"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
EPIC_LOG="$METRICS_DIR/epic-task-detector.jsonl"

# Session-aware metrics directory
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  _SESSION_FILE="$PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  [ -f "$_SESSION_FILE" ] && SESSION_ID=$(cat "$_SESSION_FILE" 2>/dev/null)
fi
if [ -n "$SESSION_ID" ]; then
  SESSION_METRICS="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/metrics"
  if [ -d "$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID" ]; then
    METRICS_DIR="$SESSION_METRICS"
    EPIC_LOG="$SESSION_METRICS/epic-task-detector.jsonl"
  fi
fi

# Read stdin (JSON with tool_name, tool_input)
INPUT=$(cat)

# Exit early if no input
if [ -z "$INPUT" ]; then
  exit 0
fi

# Require jq
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Only process Agent tool
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [ "$TOOL_NAME" != "Agent" ]; then
  exit 0
fi

# Extract agent prompt/description
AGENT_PROMPT=$(echo "$INPUT" | jq -r '
  .tool_input.prompt // .tool_input.description // ""
' 2>/dev/null)

if [ -z "$AGENT_PROMPT" ] || [ "$AGENT_PROMPT" = "null" ]; then
  exit 0
fi

# --- Epic Task Detection ---
SIGNALS=""
SIGNAL_COUNT=0

add_signal() {
  SIGNAL_COUNT=$((SIGNAL_COUNT + 1))
  if [ -z "$SIGNALS" ]; then
    SIGNALS="$1"
  else
    SIGNALS="$SIGNALS\n$1"
  fi
}

# Signal 1: "all files" / "every file" / "across all"
if echo "$AGENT_PROMPT" | grep -qiE '\b(all|every)\b.{0,15}\bfiles?\b'; then
  add_signal "SCOPE: 'all/every files' detected — likely affects many files"
fi

# Signal 2: "every service" / "all services" / "each service"
if echo "$AGENT_PROMPT" | grep -qiE '\b(all|every|each)\b.{0,15}\b(service|microservice|module|package)s?\b'; then
  add_signal "SCOPE: 'all/every services' detected — cross-service task"
fi

# Signal 3: "across the codebase" / "throughout the project" / "entire repo"
if echo "$AGENT_PROMPT" | grep -qiE '\b(across|throughout|entire|whole)\b.{0,20}\b(codebase|project|repo|repository|monorepo)\b'; then
  add_signal "SCOPE: 'across/throughout codebase' detected — full-repo scope"
fi

# Signal 4: "bulk" / "mass" / "batch" operations
if echo "$AGENT_PROMPT" | grep -qiE '\b(bulk|mass|batch)\b.{0,20}\b(update|change|replace|rename|modify|refactor)\b'; then
  add_signal "SCOPE: bulk/mass operation detected"
fi

# Signal 5: "rebrand" / "rename everywhere" / "migrate all"
if echo "$AGENT_PROMPT" | grep -qiE '\b(rebrand|rename everywhere|migrate all|replace all occurrences)\b'; then
  add_signal "SCOPE: rebrand/rename/migrate-all detected — high file count expected"
fi

# Signal 6: Explicit file counts >20
if echo "$AGENT_PROMPT" | grep -oE '[0-9]+' | while read -r NUM; do
  if [ "$NUM" -ge 20 ] 2>/dev/null; then
    exit 1  # Found a number >= 20
  fi
done; then
  : # No large numbers found
else
  add_signal "SCOPE: file count >= 20 mentioned in prompt"
fi

# Signal 7: sed/grep applied to glob patterns
if echo "$AGENT_PROMPT" | grep -qiE "sed\b.{0,30}(\*\.|glob|\\\$\(grep|xargs)"; then
  add_signal "RISK: sed applied to glob/grep output — mechanical change at scale"
fi

# Signal 8: "find and replace" at scale
if echo "$AGENT_PROMPT" | grep -qiE '\b(find and replace|search and replace|global replace)\b'; then
  add_signal "RISK: global find-and-replace detected"
fi

# --- Report ---
if [ "$SIGNAL_COUNT" -ge 2 ]; then
  # Log the detection
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  mkdir -p "$METRICS_DIR" 2>/dev/null
  AGENT_DESC=$(echo "$AGENT_PROMPT" | head -c 100)
  ENTRY="{\"timestamp\":\"$TIMESTAMP\",\"signals\":$SIGNAL_COUNT,\"agent\":$(echo "$AGENT_DESC" | jq -Rs .)}"
  safe_jsonl_append "$EPIC_LOG" "$ENTRY"

  echo ""
  echo "=== EPIC TASK DETECTED ($SIGNAL_COUNT signals) ==="
  echo ""
  echo "This task appears to affect a large number of files."
  echo ""
  echo "Signals detected:"
  echo -e "$SIGNALS"
  echo ""
  echo "RECOMMENDATION: Run /sandbox-sample first to validate the change strategy"
  echo "on a small subset before applying to all files."
  echo ""
  echo "Why: Without sampling, agents apply changes blindly. Documentation gets"
  echo "broken by sed, configs get corrupted, and 'done' means 'I ran sed on everything.'"
  echo ""
  echo "This check is ADVISORY — the agent will still launch."
  echo ""
  echo "=== END EPIC TASK DETECTION ==="
  echo ""
elif [ "$SIGNAL_COUNT" -eq 1 ]; then
  # Single signal — lighter warning, just log
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  mkdir -p "$METRICS_DIR" 2>/dev/null
  AGENT_DESC=$(echo "$AGENT_PROMPT" | head -c 100)
  ENTRY="{\"timestamp\":\"$TIMESTAMP\",\"signals\":$SIGNAL_COUNT,\"agent\":$(echo "$AGENT_DESC" | jq -Rs .)}"
  safe_jsonl_append "$EPIC_LOG" "$ENTRY"
fi

exit 0
