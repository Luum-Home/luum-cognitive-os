#!/usr/bin/env bash
# SCOPE: both
# UserPromptSubmit hook — auto-suggest /session-wrapup when user signals close.
# ADR-030 Q1. Advisory only (exit 0 always). Emits additionalContext to the
# orchestrator when the prompt matches a closure regex.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# Read stdin JSON, extract user_prompt
INPUT=""
if [ ! -t 0 ]; then
    INPUT=$(cat 2>/dev/null || true)
fi
[ -z "$INPUT" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0

PROMPT=$(echo "$INPUT" | jq -r '.user_prompt // .prompt // empty' 2>/dev/null || true)
[ -z "$PROMPT" ] && exit 0

# Closure-intent regex (case-insensitive).
# Match explicit session-close intent only.
CLOSURE_RE='close[[:space:]]+(the[[:space:]]+)?session|end[[:space:]]+(the[[:space:]]+)?session|session[[:space:]]+(close|end|wrap[[:space:]]*up)|wrap[[:space:]]+up[[:space:]]+the[[:space:]]+session|we[[:space:]]+are[[:space:]]+done|done[[:space:]]+for[[:space:]]+(today|now)|finish[[:space:]]+(the[[:space:]]+)?session'

if echo "$PROMPT" | grep -qiE "$CLOSURE_RE"; then
    # Emit additionalContext per ADR-023 pattern
    jq -c -n '{
      hookSpecificOutput: {
        hookEventName: "UserPromptSubmit",
        additionalContext: "AUTO-TRIGGER: user requested session close. Invoke /session-wrapup before any other action. Do not skip. (See ADR-030 Q1 / hooks/session-wrapup-trigger.sh)"
      }
    }'

    # ADR-030 §Testing: log emission for log-then-reconcile compliance test.
    # Degrade silently on any Python error — never block the hook.
    _PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
    _SESSION_ID="${COGNITIVE_OS_SESSION_ID:-unknown}"
    _PROMPT_DIGEST=$(printf '%s' "$PROMPT" | sha256sum 2>/dev/null | cut -c1-8 || printf 'xxxxxxxx')
    _MATCHED_PHRASE=$(echo "$PROMPT" | grep -oiE "$CLOSURE_RE" | head -1 | cut -c1-40 || true)
    _PY=$(command -v python3 || command -v python || true)
    if [ -n "$_PY" ]; then
        COGNITIVE_OS_PROJECT_DIR="$_PROJECT_DIR" \
        "$_PY" - "$_PROJECT_DIR" "$_SESSION_ID" "$_PROMPT_DIGEST" "$_MATCHED_PHRASE" \
            </dev/null >/dev/null 2>&1 <<'PYEOF' || true
import os, sys
root = sys.argv[1]
sys.path.insert(0, root)
try:
    from lib.metric_event import MetricEvent, append_event
    event = MetricEvent(
        source="session-wrapup-trigger",
        event_type="auto_trigger.emitted",
        payload={
            "suggested_skill": "session-wrapup",
            "prompt_digest": sys.argv[3],
            "session_id": sys.argv[2],
            "matched_phrase": sys.argv[4],
        },
    )
    out = os.path.join(root, ".cognitive-os", "metrics", "auto-trigger-events.jsonl")
    append_event(out, event)
except Exception:
    pass
PYEOF
    fi
fi

exit 0
