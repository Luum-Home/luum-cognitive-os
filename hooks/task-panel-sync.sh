#!/usr/bin/env bash
# SCOPE: os-only
# Task Panel Sync — exposes COS task state to Claude Code's native UI.
#
# Implements ADR-021 (vendor-agnostic state with provider adapters).
# PostToolUse hook on Agent. Async — never blocks tool execution.
#
# Reads .cognitive-os/tasks/active-tasks.json and emits additionalContext
# so the agent sees COS orchestration state (circuit breaker, queue,
# workload scheduler) that's invisible in Claude Code's native Task panel.

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

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
#
# What dies with this adapter: the additionalContext block carrying COS
# orchestration state — circuit breaker, dispatch queue, workload scheduler —
# which is invisible in Claude Code's native Task panel. When it fails the agent
# keeps planning as if no gate existed, which is exactly the failure this hook
# was written to prevent, so it must not fail quietly.
# stdout stays the protocol channel (hookSpecificOutput); the diagnosis goes to
# stderr, and the exit code stays 0 so the tool result is never blocked.
_TPS_ERR=$(mktemp "${TMPDIR:-/tmp}/cos-task-panel-adapter.err.XXXXXX" 2>/dev/null || printf '/tmp/cos-task-panel-adapter-err-%s' "$$")
_TPS_RC=0
python3 "$(dirname "$0")/_lib/task_panel_adapter.py" 2>"$_TPS_ERR" || _TPS_RC=$?
if [ "$_TPS_RC" -ne 0 ]; then
  echo "TASK PANEL SYNC: _lib/task_panel_adapter.py failed (exit ${_TPS_RC}) — COS task state (circuit breaker / queue / scheduler) is NOT in this context window." >&2
fi
if [ -s "$_TPS_ERR" ]; then
  head -20 "$_TPS_ERR" >&2
fi
rm -f "$_TPS_ERR" 2>/dev/null || true

exit 0
