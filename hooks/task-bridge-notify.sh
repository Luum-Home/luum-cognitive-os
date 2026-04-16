#!/usr/bin/env bash
# Task Bridge Notify — exposes COS task state to Claude Code (ADR-024)
#
# PostToolUse hook on Agent. Async — never blocks.
# Reads .cognitive-os/tasks/active-tasks.json + rate-limit-queue.json
# Emits hookSpecificOutput.additionalContext with queued/in-progress state
# so the model sees what's invisible in the native Task panel.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Read stdin to detect the completed tool_use_id (for correlation)
INPUT=$(cat 2>/dev/null || echo "{}")

# Only emit context if running under Claude Code
if [ -z "${CLAUDE_PROJECT_DIR:-}" ] && [ -z "${CLAUDE_SESSION_ID:-}" ]; then
  exit 0
fi

# Mark task complete by tool_use_id if available
if command -v jq &>/dev/null; then
  TOOL_USE_ID=$(echo "$INPUT" | jq -r '.tool_use_id // empty' 2>/dev/null)
  if [ -n "$TOOL_USE_ID" ]; then
    # Fire-and-forget completion registration (non-blocking)
    python3 "$(dirname "$0")/_lib/task_bridge.py" complete \
      --tool-use-id "$TOOL_USE_ID" \
      --summary "" >/dev/null 2>&1 || true
  fi
fi

# Emit additionalContext with state summary
python3 "$(dirname "$0")/_lib/task_bridge.py" panel-context 2>/dev/null || true

exit 0
