#!/usr/bin/env bash
# SCOPE: os-only
# PostToolUse hook: Tool Sequence Capture
#
# Appends one JSONL line per tool invocation to
#   .cognitive-os/metrics/tool-sequences.jsonl
#
# Schema (one line per invocation):
#   {"timestamp":"...","session_id":"...","task_id":"...","tool":"Bash|Edit|...","args_hash":"<sha256[:8]>","success":true|false}
#   Bash adds: command_hash, command_family, command_preview (redacted, <=180 chars)
#   Loop warnings are emitted from the same stream; the old standalone
#   tool-loop-detector hook is intentionally not projected.
#
# PERFORMANCE CONTRACT:
#   <30ms overhead per call. Pure shell. NO python3 per invocation.
#   Atomic single-line >> append. Bash command_preview is capped and redacted;
#   line size stays below POSIX PIPE_BUF (512 bytes).
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
_hash8() {
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "$1" | shasum -a 256 2>/dev/null | cut -c1-8 || echo '00000000'
  elif command -v sha256sum >/dev/null 2>&1; then
    printf '%s' "$1" | sha256sum 2>/dev/null | cut -c1-8 || echo '00000000'
  else
    echo '00000000'
  fi
}

_json_string() {
  printf '%s' "$1" | jq -Rs . 2>/dev/null || printf '""'
}

_redact_bash_preview() {
  # Preserve enough command shape for bypass/sequence analysis while removing
  # common inline credentials. Keep this pure shell+sed for hot-path portability.
  printf '%s' "$1" \
    | tr '\n\r\t' '   ' \
    | sed -E \
      -e 's/(^|[[:space:]])([A-Za-z_][A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|PASS|CREDENTIAL|AUTH)[A-Za-z0-9_]*=)[^[:space:]]+/\1\2[REDACTED]/Ig' \
      -e 's/(--?(api[-_]?key|token|secret|password|pass|credential|auth)(=|[[:space:]]+))[^[:space:]]+/\1[REDACTED]/Ig' \
      -e 's/(Bearer[[:space:]]+)[A-Za-z0-9._~+\/-]+/\1[REDACTED]/Ig' \
    | cut -c1-180
}

_command_family() {
  local cmd="$1"
  # Strip leading env assignments and common wrappers so sequence analysis sees
  # the command primitive instead of a one-off variable name.
  printf '%s' "$cmd" | awk '{
    for (i=1; i<=NF; i++) {
      if ($i ~ /^[A-Za-z_][A-Za-z0-9_]*=/) continue
      if ($i == "env" || $i == "command" || $i == "sudo") continue
      print $i
      exit
    }
  }' | sed -E 's#[;&|()].*$##' | cut -c1-48
}

TOOL_INPUT_RAW=$(echo "$_STDIN_JSON" | jq -c '.tool_input // {}' 2>/dev/null || echo '{}')
ARGS_HASH=$(_hash8 "$TOOL_INPUT_RAW")

# ── Bash command shape (safe, redacted, useful for bypass detection) ─────────
BASH_FIELDS=""
if [ "$TOOL_NAME" = "Bash" ]; then
  COMMAND_RAW=$(echo "$_STDIN_JSON" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
  if [ -n "$COMMAND_RAW" ]; then
    COMMAND_HASH=$(_hash8 "$COMMAND_RAW")
    COMMAND_FAMILY=$(_command_family "$COMMAND_RAW")
    COMMAND_PREVIEW=$(_redact_bash_preview "$COMMAND_RAW")
    COMMAND_FAMILY_JSON=$(_json_string "$COMMAND_FAMILY")
    COMMAND_PREVIEW_JSON=$(_json_string "$COMMAND_PREVIEW")
    BASH_FIELDS=",\"command_hash\":\"${COMMAND_HASH}\",\"command_family\":${COMMAND_FAMILY_JSON},\"command_preview\":${COMMAND_PREVIEW_JSON}"
  fi
fi

# ── Timestamp ────────────────────────────────────────────────────────────────
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)

# ── Build JSON line (no python3) ─────────────────────────────────────────────
JSON_LINE="{\"timestamp\":\"${TIMESTAMP}\",\"session_id\":\"${SESSION_ID}\",\"task_id\":\"${TASK_ID}\",\"tool\":\"${TOOL_NAME}\",\"args_hash\":\"${ARGS_HASH}\"${BASH_FIELDS},\"success\":${SUCCESS}}"

# ── Append to JSONL ──────────────────────────────────────────────────────────
METRICS_DIR=$(_resolve_metrics_dir)
TARGET="$METRICS_DIR/tool-sequences.jsonl"

# Ensure parent exists (safe-jsonl.sh may not have created the file-specific dir)
[ -d "$METRICS_DIR" ] || mkdir -p "$METRICS_DIR" 2>/dev/null

_signature_from_jsonl() {
  jq -r '"\(.tool // "unknown")|\(.args_hash // "00000000")"' 2>/dev/null || true
}

CURRENT_SIGNATURE="${TOOL_NAME}|${ARGS_HASH}"
if [ -f "$TARGET" ]; then
  LAST_2=$(tail -n 2 "$TARGET" 2>/dev/null | _signature_from_jsonl)
  if [ "$(printf '%s\n%s\n' "$LAST_2" "$CURRENT_SIGNATURE" | grep -cF "$CURRENT_SIGNATURE" || true)" -ge 3 ]; then
    echo "TOOL LOOP DETECTED: generic_repeat" >&2
    echo "Tool "${TOOL_NAME}" called 3+ times in a row with the same arguments." >&2
    echo "Consider: changing approach, reading a different file, or asking the user." >&2
  fi

  LAST_3=$(tail -n 3 "$TARGET" 2>/dev/null | _signature_from_jsonl)
  if [ "$(printf '%s\n' "$LAST_3" | wc -l | tr -d ' ')" -ge 3 ]; then
    SIG_A=$(printf '%s\n' "$LAST_3" | sed -n '1p')
    SIG_B=$(printf '%s\n' "$LAST_3" | sed -n '2p')
    SIG_C=$(printf '%s\n' "$LAST_3" | sed -n '3p')
    if [ "$SIG_A" = "$SIG_C" ] && [ "$SIG_B" = "$CURRENT_SIGNATURE" ] && [ "$SIG_A" != "$SIG_B" ]; then
      TOOL_A=${SIG_A%%|*}
      TOOL_B=${SIG_B%%|*}
      echo "TOOL LOOP DETECTED: ping_pong" >&2
      echo "Tools "${TOOL_A}" and "${TOOL_B}" are alternating back and forth." >&2
      echo "Consider: consolidating your approach, or trying a different strategy." >&2
    fi
  fi
fi

# Single atomic >> append (safe for lines < PIPE_BUF on macOS/Linux)
echo "$JSON_LINE" >> "$TARGET"

exit 0
