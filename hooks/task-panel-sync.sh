#!/usr/bin/env bash
# Task Panel Sync — exposes COS task state to Claude Code's native UI.
#
# Implements ADR-021 (vendor-agnostic state with provider adapters).
# PostToolUse hook on Agent. Async — never blocks tool execution.
#
# Reads .cognitive-os/tasks/active-tasks.json and emits additionalContext
# so the agent sees COS orchestration state (circuit breaker, queue,
# workload scheduler) that's invisible in Claude Code's native Task panel.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Only run under Claude Code — other providers have their own adapters
if [ -z "${CLAUDE_PROJECT_DIR:-}" ] && [ -z "${CLAUDE_SESSION_ID:-}" ]; then
  exit 0
fi

# Read stdin to check if this is an Agent tool call
INPUT=$(cat 2>/dev/null || echo "{}")
if command -v jq &>/dev/null; then
  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
  if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Agent" ]; then
    exit 0
  fi
fi

# Run adapter (always exits 0; emits hookSpecificOutput or nothing)
python3 "$(dirname "$0")/_lib/task_panel_adapter.py" 2>/dev/null || true

exit 0
