#!/usr/bin/env bash
# normalize-stdin.sh — Stdin normalization layer for Cognitive OS hooks
#
# Abstracts the JSON input format so hooks work across different AI coding
# tools: Claude Code, Cursor, Windsurf, OpenCode, Kiro.
#
# Usage:
#   source "$(dirname "$0")/_lib/normalize-stdin.sh"
#
# Exported variables (tool-agnostic):
#   HOOK_TOOL_NAME      — Tool being used: Agent, Bash, Edit, Write, Read, Glob, Grep
#   HOOK_TOOL_INPUT     — Full JSON object of tool input
#   HOOK_TOOL_RESPONSE  — Full text of tool response (PostToolUse only)
#   HOOK_TOOL_PROMPT    — Agent prompt (for Agent tools)
#   HOOK_TOOL_DESC      — Agent description (for Agent tools)
#   HOOK_RAW_INPUT      — Original raw stdin (for fallback / re-parsing)
#   HOOK_SOURCE_TOOL    — Which IDE: claude-code, cursor, windsurf, opencode, kiro, unknown
#
# Helper functions:
#   hook_get_field <jq_path> [default]  — extract a field from HOOK_RAW_INPUT
#
# Design constraints:
#   - Reads stdin ONCE (stream — cannot be re-read)
#   - Single jq invocation per field extraction (performance)
#   - < 50ms overhead on typical hook inputs
#   - Handles empty stdin gracefully (all vars set to empty strings)
#   - Gracefully degrades when jq is not available
#   - Idempotent: sourcing multiple times is a no-op
#
# Compatibility matrix:
#
#   Tool          | tool_name field       | tool_input field | response field
#   --------------|----------------------|------------------|---------------
#   Claude Code   | .tool_name           | .tool_input      | .tool_response
#   Cursor        | .toolName            | .toolInput       | .toolOutput
#   Windsurf      | .agent_action_name   | .tool_info       | .result
#   Kiro          | .tool_name           | .tool_input      | .tool_result
#   OpenCode      | (JS plugin API)      | —                | —
#   Unknown       | —                    | —                | —

# ─── Guard: only load once ───────────────────────────────────────────────────
[ "${_NORMALIZE_STDIN_SH_LOADED:-}" = "true" ] && return 0
_NORMALIZE_STDIN_SH_LOADED="true"

# ─── Initialize export variables to safe defaults ────────────────────────────
export HOOK_TOOL_NAME=""
export HOOK_TOOL_INPUT=""
export HOOK_TOOL_RESPONSE=""
export HOOK_TOOL_PROMPT=""
export HOOK_TOOL_DESC=""
export HOOK_RAW_INPUT=""
export HOOK_SOURCE_TOOL="unknown"

# ─── Read stdin ONCE ─────────────────────────────────────────────────────────
# Recommended source order in hooks:
#   source "$(dirname "$0")/_lib/common.sh"
#   source "$(dirname "$0")/_lib/normalize-stdin.sh"
#
# When common.sh is sourced first it reads stdin into $_STDIN_JSON and sets
# $_STDIN_READ="true". We reuse that cache.  When sourced first (rare), we read
# stdin ourselves and pre-populate the common.sh cache variables so that
# stdin_field() / require_tool() still work correctly even though common.sh
# initialises those vars to empty at load time — we overwrite them right after.
if [ "${_STDIN_READ:-false}" = "true" ] && [ -n "${_STDIN_JSON:-}" ]; then
  # common.sh already consumed stdin — reuse its cache
  HOOK_RAW_INPUT="$_STDIN_JSON"
else
  HOOK_RAW_INPUT=$(cat)
fi

# Always ensure common.sh cache is populated with our raw input so that
# stdin_field() / require_tool() work regardless of source order.
_STDIN_JSON="$HOOK_RAW_INPUT"
_STDIN_READ="true"

# Empty stdin — nothing to parse; leave all variables empty
if [ -z "$HOOK_RAW_INPUT" ]; then
  HOOK_SOURCE_TOOL="unknown"
  return 0
fi

# ─── jq availability check ───────────────────────────────────────────────────
_HAS_JQ=false
command -v jq >/dev/null 2>&1 && _HAS_JQ=true

# ─── Detection + normalization ───────────────────────────────────────────────
if [ "$_HAS_JQ" = "true" ]; then
  # Single jq call that detects schema and extracts all fields at once.
  # Outputs tab-separated: source_tool\ttool_name\ttool_input\ttool_response\tprompt\tdesc
  _PARSED=$(echo "$HOOK_RAW_INPUT" | jq -r '
    if has("tool_name") and has("tool_input") and (has("tool_result") or has("tool_response")) then
      # Kiro (tool_result) vs Claude Code (tool_response)
      "kiro-or-claude",
      (.tool_name // ""),
      (.tool_input | tojson),
      (.tool_result // .tool_response // ""),
      (.tool_input.prompt // .tool_input.description // ""),
      (.tool_input.description // "")
    elif has("tool_name") and has("tool_input") then
      # Claude Code (PreToolUse — no response yet)
      "claude-code",
      (.tool_name // ""),
      (.tool_input | tojson),
      "",
      (.tool_input.prompt // .tool_input.description // ""),
      (.tool_input.description // "")
    elif has("toolName") and has("toolInput") then
      # Cursor
      "cursor",
      (.toolName // ""),
      (.toolInput | tojson),
      (.toolOutput // ""),
      (.toolInput.prompt // .toolInput.description // ""),
      (.toolInput.description // "")
    elif has("agent_action_name") then
      # Windsurf
      "windsurf",
      (.agent_action_name // ""),
      (if has("tool_info") then (.tool_info | tojson) else "{}" end),
      (.result // ""),
      (.tool_info.prompt // .tool_info.description // ""),
      (.tool_info.description // "")
    else
      # Unknown / fallback
      "unknown",
      "",
      "{}",
      "",
      "",
      ""
    end
  ' 2>/dev/null || true)

  # Parse the tab/newline separated output into variables
  if [ -n "$_PARSED" ]; then
    _SRC=$(echo "$_PARSED" | sed -n '1p')
    _RAW_TOOL=$(echo "$_PARSED" | sed -n '2p')
    _RAW_INPUT_JSON=$(echo "$_PARSED" | sed -n '3p')
    _RAW_RESPONSE=$(echo "$_PARSED" | sed -n '4p')
    _RAW_PROMPT=$(echo "$_PARSED" | sed -n '5p')
    _RAW_DESC=$(echo "$_PARSED" | sed -n '6p')

    # Disambiguate kiro-or-claude by checking for tool_result vs tool_response
    if [ "$_SRC" = "kiro-or-claude" ]; then
      if echo "$HOOK_RAW_INPUT" | jq -e 'has("tool_result")' >/dev/null 2>&1; then
        HOOK_SOURCE_TOOL="kiro"
      else
        HOOK_SOURCE_TOOL="claude-code"
      fi
    else
      HOOK_SOURCE_TOOL="$_SRC"
    fi

    HOOK_TOOL_NAME="$_RAW_TOOL"
    HOOK_TOOL_INPUT="$_RAW_INPUT_JSON"
    HOOK_TOOL_RESPONSE="$_RAW_RESPONSE"
    HOOK_TOOL_PROMPT="$_RAW_PROMPT"
    HOOK_TOOL_DESC="$_RAW_DESC"
  fi

else
  # ── Fallback: no jq — use grep-based heuristics ──────────────────────────
  # This is intentionally minimal — no complex parsing without jq.

  if echo "$HOOK_RAW_INPUT" | grep -q '"tool_name"'; then
    HOOK_SOURCE_TOOL="claude-code"
    HOOK_TOOL_NAME=$(echo "$HOOK_RAW_INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' \
      | head -1 | sed 's/.*"tool_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  elif echo "$HOOK_RAW_INPUT" | grep -q '"toolName"'; then
    HOOK_SOURCE_TOOL="cursor"
    HOOK_TOOL_NAME=$(echo "$HOOK_RAW_INPUT" | grep -o '"toolName"[[:space:]]*:[[:space:]]*"[^"]*"' \
      | head -1 | sed 's/.*"toolName"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  elif echo "$HOOK_RAW_INPUT" | grep -q '"agent_action_name"'; then
    HOOK_SOURCE_TOOL="windsurf"
    HOOK_TOOL_NAME=$(echo "$HOOK_RAW_INPUT" | grep -o '"agent_action_name"[[:space:]]*:[[:space:]]*"[^"]*"' \
      | head -1 | sed 's/.*"agent_action_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  else
    HOOK_SOURCE_TOOL="unknown"
  fi

  # Raw input is the best we can do without jq
  HOOK_TOOL_INPUT="$HOOK_RAW_INPUT"
fi

# ─── hook_get_field ──────────────────────────────────────────────────────────
# Extract a field from HOOK_RAW_INPUT using a jq path.
#
# Usage: hook_get_field '.tool_input.file_path' '/default/path'
# Usage: hook_get_field '.toolInput.filePath'
#
# Uses jq when available; falls back to empty string + default.

hook_get_field() {
  local path="$1"
  local default="${2:-}"

  if [ "$_HAS_JQ" = "true" ] && [ -n "$HOOK_RAW_INPUT" ]; then
    local val
    val=$(echo "$HOOK_RAW_INPUT" | jq -r "${path} // empty" 2>/dev/null)
    if [ -z "$val" ] || [ "$val" = "null" ]; then
      echo "$default"
    else
      echo "$val"
    fi
  else
    echo "$default"
  fi
}
