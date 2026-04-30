#!/usr/bin/env bash
# SCOPE: os-only
# PostToolUse hook: Tool Sequence Capture
#
# Appends one JSONL line per tool invocation to
#   .cognitive-os/metrics/tool-sequences.jsonl
#
# Schema (one line per invocation):
#   {"timestamp":"...","session_id":"...","task_id":"...","tool":"Bash|Edit|...","args_hash":"<sha256[:8]>","success":true|false}
#
# PERFORMANCE CONTRACT:
#   <30ms overhead per call. Pure shell. NO python3 per invocation.
#   Atomic single-line >> append (safe for concurrent writers when
#   line size < PIPE_BUF, which is 512 bytes on POSIX / 4KB on macOS).
#
# ADR-095: Phase 2 — tool-sequence instrumentation for skill synthesis.

set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
_HOOK_NAME="tool-sequence-capture"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode

# ── Read stdin (cached by read_stdin_json) ───────────────────────────────────
read_stdin_json

TOOL_NAME=$(stdin_field '.tool_name' '')
[ -z "$TOOL_NAME" ] && exit 0

# ── Session / task ID ────────────────────────────────────────────────────────
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-}}"
if [ -z "$SESSION_ID" ]; then
  SESSION_ID="${PPID:-0}"
fi

TASK_ID="${COS_TASK_ID:-}"
if [ -z "$TASK_ID" ]; then
  # Derive a stable per-session pseudo-task id from session+timestamp second
  TASK_ID="session-${SESSION_ID}"
fi

# ── Detect success ───────────────────────────────────────────────────────────
TOOL_OUTPUT=$(stdin_field '.tool_response.content' '')
if [ -z "$TOOL_OUTPUT" ]; then
  TOOL_OUTPUT=$(echo "$_STDIN_JSON" | jq -r \
    'if .tool_response | type == "array" then .tool_response[].text // "" else .tool_response // "" end' \
    2>/dev/null || true)
fi

SUCCESS=true
if echo "$TOOL_OUTPUT" | grep -qiE '(Error|Exception|FAIL|build failed|test failed|ESCALATION|exit code [1-9])' 2>/dev/null; then
  SUCCESS=false
fi

# Also check exit_code field if present
TOOL_EXIT=$(stdin_field '.tool_response.exit_code' '')
if [ -n "$TOOL_EXIT" ] && [ "$TOOL_EXIT" != "0" ] && [ "$TOOL_EXIT" != "null" ]; then
  SUCCESS=false
fi

# ── Args hash (PII-safe sha256[:8]) ─────────────────────────────────────────
# Serialize tool_input to a stable string and sha256. No python3.
TOOL_INPUT_RAW=$(echo "$_STDIN_JSON" | jq -c '.tool_input // {}' 2>/dev/null || echo '{}')
if command -v shasum >/dev/null 2>&1; then
  ARGS_HASH=$(printf '%s' "$TOOL_INPUT_RAW" | shasum -a 256 2>/dev/null | cut -c1-8 || echo '00000000')
elif command -v sha256sum >/dev/null 2>&1; then
  ARGS_HASH=$(printf '%s' "$TOOL_INPUT_RAW" | sha256sum 2>/dev/null | cut -c1-8 || echo '00000000')
else
  ARGS_HASH='00000000'
fi

# ── Timestamp ────────────────────────────────────────────────────────────────
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)

# ── Build JSON line (no python3, no jq for construction) ────────────────────
JSON_LINE="{\"timestamp\":\"${TIMESTAMP}\",\"session_id\":\"${SESSION_ID}\",\"task_id\":\"${TASK_ID}\",\"tool\":\"${TOOL_NAME}\",\"args_hash\":\"${ARGS_HASH}\",\"success\":${SUCCESS}}"

# ── Append to JSONL ──────────────────────────────────────────────────────────
METRICS_DIR=$(_resolve_metrics_dir)
TARGET="$METRICS_DIR/tool-sequences.jsonl"

# Ensure parent exists (safe-jsonl.sh may not have created the file-specific dir)
[ -d "$METRICS_DIR" ] || mkdir -p "$METRICS_DIR" 2>/dev/null

# Single atomic >> append (safe for lines < PIPE_BUF on macOS/Linux)
echo "$JSON_LINE" >> "$TARGET"

exit 0
