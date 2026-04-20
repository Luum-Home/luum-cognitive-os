#!/usr/bin/env bash
# skill-usage-tracker.sh — PostToolUse hook for the Skill tool.
#
# PURPOSE
#   Capture runtime usage of skills into a JSONL telemetry file so the
#   observability aggregator (`cos usage`) can answer questions like
#   "of the N exposed skills, which were actually invoked?".
#
# CONTRACT
#   - Event:        PostToolUse (matcher: Skill)
#   - Blocking:     NO. Always exits 0, even on parse errors.
#   - Side effects: appends one line to .cognitive-os/metrics/skill-usage.jsonl
#   - Latency:      best-effort; runs async-in-background to be safe.
#
# REGISTRATION
#   This hook is NOT yet registered in .claude/settings.json.
#   Follow-up (UX8+): add to `apply-efficiency-profile.sh` default tier so the
#   self-install flow picks it up. Until then, register manually if you want
#   live telemetry:
#     {
#       "event":   "PostToolUse",
#       "matcher": "Skill",
#       "hooks":   [{ "type": "command",
#                     "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/skill-usage-tracker.sh\"" }]
#     }

set -uo pipefail

# Read stdin up-front (fast, local copy) so we can safely background the
# heavy work below. Reading in the foreground avoids the subtle issue where a
# backgrounded subshell can lose its stdin if the parent exits first.
INPUT="$(cat 2>/dev/null || true)"

# No input = nothing to record. Exit silently but still 0.
[ -z "$INPUT" ] && exit 0

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"

# Extract just the skill name — portable: prefer jq, fall back to sed.
SKILL_NAME=""
if command -v jq >/dev/null 2>&1; then
  # Tool name must be "Skill"; ignore anything else (defensive).
  TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
  [ "$TOOL" != "Skill" ] && exit 0
  SKILL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_input.skill // .tool_input.name // empty' 2>/dev/null)
else
  # No jq → grep the first "skill" or "name" field. Safe on malformed JSON.
  SKILL_NAME=$(printf '%s' "$INPUT" \
    | sed -n 's/.*"skill"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    | head -1)
  [ -z "$SKILL_NAME" ] && SKILL_NAME=$(printf '%s' "$INPUT" \
    | sed -n 's/.*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    | head -1)
fi

[ -z "$SKILL_NAME" ] && exit 0

# Pull duration if the harness provided one (ms). Default to 0.
DURATION_MS=0
if command -v jq >/dev/null 2>&1; then
  D=$(printf '%s' "$INPUT" | jq -r '.tool_response.duration_ms // .duration_ms // 0' 2>/dev/null)
  case "$D" in
    ''|null|0) DURATION_MS=0 ;;
    *)         DURATION_MS="$D" ;;
  esac
fi

PY=$(command -v python3 || command -v python || true)
[ -z "$PY" ] && exit 0

# Delegate the actual write to the Python telemetry module in the background
# so we never delay the tool call. Python owns rotation, locking semantics,
# and JSON encoding uniformly with the rest of the stack.
(
  COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" \
    "$PY" - "$SKILL_NAME" "$DURATION_MS" <<'PYEOF' >/dev/null 2>&1
import os, sys
# Make lib/ importable regardless of caller CWD.
root = os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()
sys.path.insert(0, root)
try:
    from lib.telemetry import record_skill_invocation
    name = sys.argv[1]
    try:
        dur = float(sys.argv[2])
    except (TypeError, ValueError):
        dur = 0.0
    record_skill_invocation(name, duration_ms=dur)
except Exception:
    # Never propagate — telemetry must not break tool execution.
    pass
PYEOF
) </dev/null >/dev/null 2>&1 &
_TRACKER_PID=$!

# ADR-028 D1.B — register with process_registry so the reaper knows this is a
# managed short-lived process and not an orphan.
(
  COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" \
    "$PY" - "$_TRACKER_PID" "skill-usage-tracker" "30" "short_lived" <<'PYEOF' >/dev/null 2>&1
import sys, os
root = os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()
sys.path.insert(0, root)
try:
    import lib.process_registry as process_registry
    process_registry.register(int(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4])
except Exception:
    pass
PYEOF
) &

# Parent returns immediately with success — background writer runs on its own.
exit 0
