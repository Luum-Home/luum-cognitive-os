#!/usr/bin/env bash
# SCOPE: both
# PreToolUse hook: Completeness Check
# Fires on "Agent" tool use — checks if the agent prompt is exhaustive enough
# Advisory only — does NOT block. Suggests running /exhaustive-prompt first.
# Must complete in <3 seconds
#
# PURPOSE: Catches vague prompts BEFORE they reach agents.
# Agents interpret ambiguity as permission to do the minimum.
# This hook detects red flags and warns the orchestrator.

set -uo pipefail

_HOOK_NAME="completeness-check"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 5
check_capability_level "completeness-check"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
COMPLETENESS_LOG="$METRICS_DIR/completeness-check.jsonl"

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
    COMPLETENESS_LOG="$SESSION_METRICS/completeness-check.jsonl"
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

# --- Red Flag Detection ---
WARNINGS=""
WARNING_COUNT=0

add_warning() {
  WARNING_COUNT=$((WARNING_COUNT + 1))
  if [ -z "$WARNINGS" ]; then
    WARNINGS="$1"
  else
    WARNINGS="$WARNINGS\n$1"
  fi
}

# Red Flag 1: "all files" without listing them
if echo "$AGENT_PROMPT" | grep -qiE '\ball\b.{0,20}\bfiles?\b' && ! echo "$AGENT_PROMPT" | grep -qiE 'FILES TO PROCESS|file list|files:$'; then
  add_warning "RED FLAG: 'all files' mentioned without listing them. Run discovery first (grep/find) and list EVERY file."
fi

# Red Flag 2: "complete the migration" without counts
if echo "$AGENT_PROMPT" | grep -qiE '\b(complete|finish|migrate)\b.{0,30}\b(migration|endpoint|service)' && ! echo "$AGENT_PROMPT" | grep -qiE '[0-9]+ (endpoint|file|service|item|route)'; then
  add_warning "RED FLAG: Migration/completion task without item count. Specify exactly HOW MANY endpoints/files/items."
fi

# Red Flag 3: "rebrand everything" / "rename all" without grep count
if echo "$AGENT_PROMPT" | grep -qiE '\b(rebrand|rename)\b.{0,20}\b(everything|all|every)\b' && ! echo "$AGENT_PROMPT" | grep -qiE 'grep|occurrence|[0-9]+ (file|match|occurrence)'; then
  add_warning "RED FLAG: Rebrand/rename 'everything' without occurrence count. Run grep first to count exact occurrences."
fi

# Red Flag 4: "follow patterns" without specifying WHICH
if echo "$AGENT_PROMPT" | grep -qiE '\bfollow\b.{0,20}\b(pattern|convention|style|approach)\b' && ! echo "$AGENT_PROMPT" | grep -qiE 'ginext|EntityWith|ControllerInterface|UseCaseInterface|example:|pattern:'; then
  add_warning "RED FLAG: 'follow patterns' without specifying WHICH patterns. List exact pattern names and examples."
fi

# Red Flag 5: No ACCEPTANCE CRITERIA section
if ! echo "$AGENT_PROMPT" | grep -qiE 'ACCEPTANCE CRITERIA|acceptance criteria'; then
  add_warning "RED FLAG: No ACCEPTANCE CRITERIA section. Every agent prompt must include measurable acceptance criteria."
fi

# Red Flag 6: "update docs" without specifying which docs
if echo "$AGENT_PROMPT" | grep -qiE '\bupdate\b.{0,15}\b(doc|documentation|readme)\b' && ! echo "$AGENT_PROMPT" | grep -qiE '[a-zA-Z0-9_-]+\.md|specific doc|which doc'; then
  add_warning "RED FLAG: 'update docs' without specifying WHICH docs. List the exact files to update."
fi

# Red Flag 7: Large scope keywords without explicit enumeration
if echo "$AGENT_PROMPT" | grep -qiE '\b(across|throughout|entire|whole|every)\b.{0,20}\b(codebase|project|repo|backend|frontend)\b' && ! echo "$AGENT_PROMPT" | grep -qiE 'SCOPE|FILES TO PROCESS|[0-9]+ (file|item|service)'; then
  add_warning "RED FLAG: Large scope ('across/throughout/entire') without explicit enumeration. Run /exhaustive-prompt first."
fi

# Red Flag 8: Generic task without verification commands
if ! echo "$AGENT_PROMPT" | grep -qiE '`[^`]+`\s*(=|>=|exits)\s*[0-9]' && ! echo "$AGENT_PROMPT" | grep -qiE 'VERIFICATION|verify|verification command'; then
  # Only flag this for non-trivial tasks
  PROMPT_LENGTH=${#AGENT_PROMPT}
  if [ "$PROMPT_LENGTH" -gt 200 ]; then
    add_warning "RED FLAG: No verification commands found. Include commands with expected results (e.g., \`command\` = 0)."
  fi
fi

# --- Report ---
if [ "$WARNING_COUNT" -gt 0 ]; then
  # Log the warning
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  mkdir -p "$METRICS_DIR" 2>/dev/null
  AGENT_DESC=$(echo "$AGENT_PROMPT" | head -c 100)
  ENTRY="{\"timestamp\":\"$TIMESTAMP\",\"warnings\":$WARNING_COUNT,\"agent\":$(echo "$AGENT_DESC" | jq -Rs .)}"
  safe_jsonl_append "$COMPLETENESS_LOG" "$ENTRY"

  echo ""
  echo "=== COMPLETENESS CHECK: $WARNING_COUNT WARNING(S) ==="
  echo ""
  echo "The agent prompt may not be exhaustive enough. Agents interpret ambiguity as permission to do the minimum."
  echo ""
  echo -e "$WARNINGS"
  echo ""
  echo "RECOMMENDATION: Run /exhaustive-prompt to generate a complete, verifiable prompt."
  echo ""
  echo "This check is ADVISORY — the agent will still launch. But quality may suffer."
  echo ""
  echo "=== END COMPLETENESS CHECK ==="
  echo ""
fi

exit 0
