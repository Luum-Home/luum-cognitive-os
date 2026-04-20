#!/usr/bin/env bash
# SCOPE: project
# PreToolUse hook on Agent — blocks agent execution when DRY_RUN=true.
# Outputs what WOULD be executed without running it. Useful for previewing
# SDD pipelines: DRY_RUN=true /sdd-ff my-feature
# Logs to .cognitive-os/metrics/dry-run.jsonl

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="dry-run-preview"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

# Only activate when DRY_RUN=true
DRY_RUN="${DRY_RUN:-false}"
if [[ "$DRY_RUN" != "true" ]]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
METRICS_DIR="$(_resolve_metrics_dir)"
DRY_RUN_LOG="$METRICS_DIR/dry-run.jsonl"

# Read input from stdin
INPUT=$(cat)

# Exit early if no input
if [[ -z "$INPUT" ]]; then
  exit 0
fi

# Require jq
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Only process Agent tool
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [[ "$TOOL_NAME" != "Agent" && "$TOOL_NAME" != "task" && "$TOOL_NAME" != "delegate" ]]; then
  exit 0
fi

# Extract task description from prompt or description field
TASK_DESC=$(echo "$INPUT" | jq -r '
  .tool_input.prompt // .tool_input.description // .tool_input.task // "(no description)"
' 2>/dev/null | head -c 500)

# Log the dry-run interception
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mkdir -p "$METRICS_DIR" 2>/dev/null
ENTRY=$(jq -c -n \
  --arg ts "$TIMESTAMP" \
  --arg tool "$TOOL_NAME" \
  --arg desc "$TASK_DESC" \
  '{timestamp: $ts, tool: $tool, task_description: $desc, action: "blocked"}')
safe_jsonl_append "$DRY_RUN_LOG" "$ENTRY"

# Output the preview message
echo ""
echo "=== DRY-RUN PREVIEW ==="
echo ""
echo "DRY-RUN: Would execute: $TASK_DESC"
echo ""
echo "Agent launch BLOCKED by DRY_RUN=true."
echo "Unset DRY_RUN or set DRY_RUN=false to execute."
echo ""
echo "=== END DRY-RUN ==="
echo ""

# Exit 2 = BLOCK the tool call
exit 2
