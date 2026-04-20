#!/usr/bin/env bash
# SCOPE: both
# PostToolUse hook: Confidence Gate (LLM-evaluated, ADR-022)
# Fires on Agent / task / delegate tool results — emits a type:"prompt"
# handler that asks Haiku whether the agent response includes a Trust
# Report (numerical confidence, evidence, acknowledged uncertainties).
# Advisory only — never blocks (the legacy confidence-gate.sh handles
# blocking when the project phase warrants it).
#
# Graceful degradation: if jq is missing, prompt-type hooks are unsupported,
# or stdin is empty/invalid, the hook exits 0 and emits nothing.
#
# Claude Code adapter for the legacy regex-based confidence-gate.sh.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="confidence-gate-llm"

_LIB_DIR="$(dirname "$0")/_lib"
[ -f "$_LIB_DIR/common.sh" ] && source "$_LIB_DIR/common.sh"

if type check_capability_level &>/dev/null; then
  check_capability_level "confidence-gate-llm"
fi

INPUT=$(cat 2>/dev/null || true)
[ -z "$INPUT" ] && exit 0

command -v jq &>/dev/null || exit 0

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
case "$TOOL_NAME" in
  Agent|task|delegate) ;;
  *) exit 0 ;;
esac

AGENT_OUTPUT=$(echo "$INPUT" | jq -r '
  .tool_result // .tool_response // .output // ""
' 2>/dev/null || true)

[ -z "$AGENT_OUTPUT" ] || [ "$AGENT_OUTPUT" = "null" ] && exit 0

AGENT_OUTPUT_TRIMMED=$(printf '%s' "$AGENT_OUTPUT" | head -c 6000)

SYSTEM_PROMPT=$(cat <<'SYS'
You are a Trust Report auditor for an agent orchestration system. The agent
is supposed to attach a Trust Report at the end of its response. A valid
Trust Report MUST contain:

(a) A numerical confidence score (e.g., "Score: 78/100" or "Trust: 78").
(b) Evidence the agent cites to justify the score (commands run, files read,
    tests passing, sources, assumptions verified).
(c) Acknowledged uncertainties or remaining risks (what the agent could NOT
    verify, what it assumed, edge cases not covered).

Read the agent response and return ONLY compact JSON:
{"has_trust_report": true|false,
 "score": <int 0-100 or null>,
 "has_evidence": true|false,
 "has_uncertainties": true|false,
 "verdict": "valid"|"missing"|"incomplete",
 "missing_pieces": ["score"|"evidence"|"uncertainties", ...]}

"valid"      = all three present (a, b, c).
"incomplete" = score present but evidence or uncertainties missing.
"missing"    = no Trust Report at all.
SYS
)

OUTPUT=$(jq -c -n \
  --arg system "$SYSTEM_PROMPT" \
  --arg user "$AGENT_OUTPUT_TRIMMED" \
  '{
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      type: "prompt",
      model: "claude-haiku-4-5",
      system: $system,
      prompt: $user,
      max_tokens: 400,
      response_format: "json",
      decision: "advisory",
      label: "confidence-gate-llm"
    }
  }' 2>/dev/null || true)

[ -z "$OUTPUT" ] && exit 0

printf '%s\n' "$OUTPUT"
exit 0
