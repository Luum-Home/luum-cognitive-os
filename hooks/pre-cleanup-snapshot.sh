#!/usr/bin/env bash
# SCOPE: project
# PreToolUse hook on Agent — detects cleanup/refactor intent and triggers capability snapshot
# Logs detections to .cognitive-os/metrics/capability-snapshots.jsonl
# Must complete in <3 seconds

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
source "$(dirname "${BASH_SOURCE[0]}")/_lib/portable.sh"

_HOOK_NAME="pre-cleanup-snapshot"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 5
check_capability_level "pre-cleanup-snapshot"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
METRICS_LOG="$PROJECT_DIR/.cognitive-os/metrics/capability-snapshots.jsonl"
CHECKPOINTS_DIR="$PROJECT_DIR/.cognitive-os/checkpoints"

# Read tool input from stdin
INPUT=$(cat)

# Only process Agent/task/delegate tool calls
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [[ "$TOOL_NAME" != "Agent" && "$TOOL_NAME" != "task" && "$TOOL_NAME" != "delegate" ]]; then
  exit 0
fi

# Extract the prompt/task description
PROMPT_TEXT=$(echo "$INPUT" | jq -r '
  (.tool_input.prompt // "") + " " +
  (.tool_input.description // "") + " " +
  (.tool_input.task // "") + " " +
  (.tool_input.instructions // "")
' 2>/dev/null | tr '[:upper:]' '[:lower:]')

if [[ -z "$PROMPT_TEXT" || "$PROMPT_TEXT" == "   " ]]; then
  exit 0
fi

# Check for cleanup/refactor keywords targeting cognitive-os
CLEANUP_PATTERN="cleanup|delete|remove|merge|consolidate|refactor agent.?os|clean.?up agent.?os|reorganize agent.?os|prune|deduplicate|simplify agent.?os"
COGNITIVE_OS_PATTERN="agent.?os|\.cognitive-os|hooks|skills|rules|squads|agents"

HAS_CLEANUP=$(echo "$PROMPT_TEXT" | grep -ciE "$CLEANUP_PATTERN" || true)
HAS_COGNITIVE_OS=$(echo "$PROMPT_TEXT" | grep -ciE "$COGNITIVE_OS_PATTERN" || true)

# Both cleanup intent AND cognitive-os scope must be present
if [[ "$HAS_CLEANUP" -eq 0 ]] || [[ "$HAS_COGNITIVE_OS" -eq 0 ]]; then
  exit 0
fi

# Check if a recent snapshot exists (within last hour = 3600 seconds)
LATEST_SNAPSHOT=$(ls -t "$CHECKPOINTS_DIR"/capability-snapshot-*.json 2>/dev/null | head -1 || true)
if [[ -n "$LATEST_SNAPSHOT" ]]; then
  SNAPSHOT_AGE=$(( $(date +%s) - $(portable_stat_mtime "$LATEST_SNAPSHOT" 2>/dev/null || echo 0) ))
  if [[ "$SNAPSHOT_AGE" -lt 3600 ]]; then
    # Recent snapshot exists, no need to warn again
    exit 0
  fi
fi

# Log detection
mkdir -p "$(dirname "$METRICS_LOG")"
ENTRY=$(jq -c -n \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg prompt "$(echo "$PROMPT_TEXT" | head -c 200)" \
  --arg tool "$TOOL_NAME" \
  '{timestamp: $ts, event: "cleanup_detected", tool: $tool, prompt_preview: $prompt}')
safe_jsonl_append "$METRICS_LOG" "$ENTRY"

# Emit advisory message (does NOT block)
cat <<'ADVISORY'
{
  "decision": "approve",
  "reason": "Cleanup/refactor of Cognitive OS detected. Recommending capability snapshot.",
  "message": "CAPABILITY PROTECTION: Cleanup/refactor intent detected targeting Cognitive OS components. Run `/capability-snapshot save` BEFORE proceeding to prevent unintended feature loss. After cleanup, run `/capability-snapshot diff` to verify no capabilities were lost."
}
ADVISORY
