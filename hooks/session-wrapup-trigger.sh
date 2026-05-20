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

REALITY_RE='primitivas?.*(controladas?|aspirational|dormant|clasificaci[oó]n|superficie|wiring|deuda)|aspirational|dormant|component[- ]?reality[- ]?check|reality[- ]?check|dogfooding|claims?[[:space:]]+aspiracionales?|antes[[:space:]]+de[[:space:]]+(release|hacerlo[[:space:]]+p[uú]blico)|merge(e|é)?[[:space:]]+(worktrees?|branches?)|agreg(u|ué|ue|ar).*(hook|skill|rule|script)|agentic[[:space:]]+primitives?'
PRIMITIVE_PATHSPEC=(hooks skills rules scripts lib manifests .cognitive-os .codex/hooks.json .claude/settings.json)

_project_dir="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$(pwd)}}}"
_is_os_repo=0
if [ -f "$_project_dir/scripts/aspirational_audit.py" ] && [ -f "$_project_dir/skills/component-reality-check/SKILL.md" ]; then
    _is_os_repo=1
fi

_has_primitive_diff=0
if [ "$_is_os_repo" -eq 1 ] && command -v git >/dev/null 2>&1 && git -C "$_project_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if [ -n "$(git -C "$_project_dir" status --porcelain -- "${PRIMITIVE_PATHSPEC[@]}" 2>/dev/null || true)" ]; then
        _has_primitive_diff=1
    fi
fi

_closure_match=0
_reality_match=0
if echo "$PROMPT" | grep -qiE "$CLOSURE_RE"; then
    _closure_match=1
fi
if echo "$PROMPT" | grep -qiE "$REALITY_RE"; then
    _reality_match=1
fi

_should_emit=0
_os_addendum=0
if [ "$_closure_match" -eq 1 ]; then
    _should_emit=1
fi
if [ "$_is_os_repo" -eq 1 ] && { [ "$_reality_match" -eq 1 ] || { [ "$_closure_match" -eq 1 ] && [ "$_has_primitive_diff" -eq 1 ]; }; }; then
    _should_emit=1
    _os_addendum=1
fi

if [ "$_should_emit" -eq 1 ]; then
    _context=""
    if [ "$_closure_match" -eq 1 ]; then
        _context="AUTO-TRIGGER: user requested session close. Invoke /session-wrapup before any other action. Do not skip. (See ADR-030 Q1 / hooks/session-wrapup-trigger.sh)"
    fi
    if [ "$_os_addendum" -eq 1 ]; then
        if [ -n "$_context" ]; then
            _context="$_context OS-ADDENDUM: Cognitive OS primitive-surface or reality-check signal detected. After /session-wrapup, invoke /os-session-wrapup addendum and run: python3 scripts/aspirational_audit.py --dry-run --json --project-root ."
        else
            _context="AUTO-TRIGGER: Cognitive OS primitive reality-check signal detected. Invoke /os-session-wrapup or run: python3 scripts/aspirational_audit.py --dry-run --json --project-root ."
        fi
    fi

    # Emit additionalContext per ADR-023 pattern
    jq -c -n --arg context "$_context" '{
      hookSpecificOutput: {
        hookEventName: "UserPromptSubmit",
        additionalContext: $context
      }
    }'

    # ADR-030 §Testing: log emission for log-then-reconcile compliance test.
    # Degrade silently on any Python error — never block the hook.
    _PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$(pwd)}}}"
    _SESSION_ID="${COGNITIVE_OS_SESSION_ID:-unknown}"
    _PROMPT_DIGEST=$(printf '%s' "$PROMPT" | sha256sum 2>/dev/null | cut -c1-8 || printf 'xxxxxxxx')
    _MATCHED_PHRASE=$(echo "$PROMPT" | grep -oiE "$CLOSURE_RE|$REALITY_RE" | head -1 | cut -c1-40 || true)
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
