#!/usr/bin/env bash
# SCOPE: os-only
# skill-invocation-logger.sh — PostToolUse hook for the Skill tool.
#
# PURPOSE
#   Log every Skill tool invocation to .cognitive-os/metrics/skill-invocations.jsonl
#   so the ADR-030 compliance test can pair AUTO-TRIGGER emissions with their
#   subsequent skill invocations within a time window.
#
# CONTRACT
#   - Event:        PostToolUse (matcher: Skill)
#   - Blocking:     NO. Always exits 0, even on parse errors.
#   - Side effects: appends one line to .cognitive-os/metrics/skill-invocations.jsonl
#   - Latency:      best-effort; Python call is cheap + any failure degrades silently.
#
# REGISTRATION
#   Registered in scripts/apply-efficiency-profile.sh default tier, PostToolUse Skill group.
#   Also documented in scripts/set-security-profile.sh standard summary.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# Read stdin JSON up-front.
INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

command -v jq >/dev/null 2>&1 || exit 0

# Only handle Skill tool calls; exit silently for anything else.
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
[ "$TOOL" != "Skill" ] && exit 0

SKILL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_input.skill // empty' 2>/dev/null || true)
SKILL_ARGS=$(printf '%s' "$INPUT" | jq -r '.tool_input.args // empty' 2>/dev/null || true)

# Truncate args to 200 chars.
SKILL_ARGS="${SKILL_ARGS:0:200}"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-unknown}"

_PY=$(command -v python3 || command -v python || true)
[ -z "$_PY" ] && exit 0

COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" \
"$_PY" - "$PROJECT_DIR" "$SESSION_ID" "$SKILL_NAME" "$SKILL_ARGS" \
    </dev/null >/dev/null 2>&1 <<'PYEOF' || true
import os, sys
root = sys.argv[1]
sys.path.insert(0, root)
try:
    from lib.metric_event import MetricEvent, append_event
    event = MetricEvent(
        source="skill-invocation-logger",
        event_type="skill.invoked",
        payload={
            "skill_name": sys.argv[3],
            "args": sys.argv[4],
            "session_id": sys.argv[2],
        },
    )
    out = os.path.join(root, ".cognitive-os", "metrics", "skill-invocations.jsonl")
    append_event(out, event)
except Exception:
    pass
PYEOF

exit 0
