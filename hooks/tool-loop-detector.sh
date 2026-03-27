#!/usr/bin/env bash
# CONCERNS: safety, quality, observability
# PostToolUse hook: Detects tool usage loops and warns the agent.
# Tracks last 10 tool calls and identifies repetitive patterns.
#
# Inspired by OpenClaw's tool loop detection pattern.
# Registered as PostToolUse hook (matcher: "*") in settings.local.json.

set -euo pipefail

source "$(dirname "$0")/_lib/common.sh"

# Use a session-stable temp file (PPID stays constant within a session)
HISTORY_FILE="/tmp/claude-tool-history-${PPID}.log"
MAX_HISTORY=10

# Read tool info from stdin (cached via common.sh)
read_stdin_json
INPUT="$_STDIN_JSON"
TOOL_NAME=$(stdin_field '.tool_name' 'unknown')
TOOL_INPUT=$(echo "$_STDIN_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('tool_input',{}), sort_keys=True)[:200])" 2>/dev/null || echo "{}")

# Create a compact signature for this call
SIGNATURE="${TOOL_NAME}|${TOOL_INPUT}"

# Append to history, keep only last N entries
echo "$SIGNATURE" >> "$HISTORY_FILE"
tail -n "$MAX_HISTORY" "$HISTORY_FILE" > "${HISTORY_FILE}.tmp" 2>/dev/null && mv "${HISTORY_FILE}.tmp" "$HISTORY_FILE"

# Read current history
LINE_COUNT=$(wc -l < "$HISTORY_FILE" 2>/dev/null | tr -d ' ')

# Skip detection if we don't have enough history
if [ "$LINE_COUNT" -lt 3 ]; then
  exit 0
fi

# --- Pattern 1: generic_repeat ---
# Same tool+args called 3+ times in a row
LAST_3=$(tail -n 3 "$HISTORY_FILE")
UNIQUE_LAST_3=$(echo "$LAST_3" | sort -u | wc -l | tr -d ' ')
if [ "$UNIQUE_LAST_3" -eq 1 ]; then
  echo "TOOL LOOP DETECTED: generic_repeat"
  echo "Tool \"${TOOL_NAME}\" called 3+ times in a row with the same arguments."
  echo "Consider: changing approach, reading a different file, or asking the user."
  exit 0
fi

# --- Pattern 2: ping_pong ---
# Two tools alternating: A->B->A->B (need 4 entries)
if [ "$LINE_COUNT" -ge 4 ]; then
  LINE_A=$(tail -n 4 "$HISTORY_FILE" | head -n 1)
  LINE_B=$(tail -n 3 "$HISTORY_FILE" | head -n 1)
  LINE_C=$(tail -n 2 "$HISTORY_FILE" | head -n 1)
  LINE_D=$(tail -n 1 "$HISTORY_FILE")

  TOOL_A=$(echo "$LINE_A" | cut -d'|' -f1)
  TOOL_B=$(echo "$LINE_B" | cut -d'|' -f1)
  TOOL_C=$(echo "$LINE_C" | cut -d'|' -f1)
  TOOL_D=$(echo "$LINE_D" | cut -d'|' -f1)

  if [ "$TOOL_A" = "$TOOL_C" ] && [ "$TOOL_B" = "$TOOL_D" ] && [ "$TOOL_A" != "$TOOL_B" ]; then
    echo "TOOL LOOP DETECTED: ping_pong"
    echo "Tools \"${TOOL_A}\" and \"${TOOL_B}\" are alternating back and forth."
    echo "Consider: consolidating your approach, or trying a different strategy."
    exit 0
  fi
fi

# --- Pattern 3: no_progress ---
# Same Read/Grep on same file 3+ times
if echo "$TOOL_NAME" | grep -qE "^(Read|Grep)$"; then
  SAME_COUNT=$(tail -n 5 "$HISTORY_FILE" | grep -cF "$SIGNATURE" || true)
  if [ "$SAME_COUNT" -ge 3 ]; then
    echo "TOOL LOOP DETECTED: no_progress"
    echo "Tool \"${TOOL_NAME}\" called ${SAME_COUNT} times on the same target."
    echo "Consider: the information you need may not be in this file, or try a different search query."
    exit 0
  fi
fi

# No loop detected
exit 0
