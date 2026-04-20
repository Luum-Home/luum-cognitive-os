#!/usr/bin/env bash
# SCOPE: os-only
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

# Closure-intent regex (case-insensitive, whole-word where helpful)
# Accented/unaccented variants + Spanish + English + common colloquial
CLOSURE_RE='cerr(a|á|emos|emosla)[[:space:]]+(la[[:space:]]+)?sesi[oó]n|session[[:space:]]+(close|end|wrap[[:space:]]*up)|terminamos|listo[,[:space:]]+(ce|cerr)|cerrar[[:space:]]+sesi[oó]n'

if echo "$PROMPT" | grep -qiE "$CLOSURE_RE"; then
    # Emit additionalContext per ADR-023 pattern
    jq -c -n '{
      hookSpecificOutput: {
        hookEventName: "UserPromptSubmit",
        additionalContext: "AUTO-TRIGGER: user requested session close. Invoke /session-wrapup before any other action. Do not skip. (See ADR-030 Q1 / hooks/session-wrapup-trigger.sh)"
      }
    }'
fi

exit 0
