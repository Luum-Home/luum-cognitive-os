#!/usr/bin/env bash
# SCOPE: both
# PreToolUse hook: Completeness Check (LLM-evaluated, ADR-022)
# Fires on "Agent" tool use — emits a type:"prompt" handler that asks Haiku
# whether the agent prompt enumerates the work to be done or hides behind
# vague quantifiers ("all", "everything", "the docs"). Advisory only.
#
# Graceful degradation: if jq is missing, prompt-type hooks are unsupported,
# or stdin is empty/invalid, the hook exits 0 and emits nothing.
#
# Claude Code adapter for the legacy regex-based completeness-check.sh.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="completeness-check-llm"

_LIB_DIR="$(dirname "$0")/_lib"
[ -f "$_LIB_DIR/common.sh" ] && source "$_LIB_DIR/common.sh"

if type check_capability_level &>/dev/null; then
  check_capability_level "completeness-check-llm"
fi
if type check_private_mode &>/dev/null; then
  check_private_mode
fi

INPUT=$(cat 2>/dev/null || true)
[ -z "$INPUT" ] && exit 0

command -v jq &>/dev/null || exit 0

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
[ "$TOOL_NAME" != "Agent" ] && exit 0

AGENT_PROMPT=$(echo "$INPUT" | jq -r '
  .tool_input.prompt // .tool_input.description // ""
' 2>/dev/null || true)

[ -z "$AGENT_PROMPT" ] || [ "$AGENT_PROMPT" = "null" ] && exit 0

AGENT_PROMPT_TRIMMED=$(printf '%s' "$AGENT_PROMPT" | head -c 4000)

SYSTEM_PROMPT=$(cat <<'SYS'
You are a completeness reviewer for agent prompts. The orchestrator is about
to dispatch work to a sub-agent. Your job is to detect prompts that hide
unbounded work behind vague quantifiers, since agents interpret ambiguity
as permission to do the minimum.

Evaluate the prompt against these criteria:
1. Does it ENUMERATE the items to process (file list, count, explicit IDs),
   or does it use vague words ("all", "every", "the entire codebase",
   "everything") without naming them?
2. Does it include ACCEPTANCE CRITERIA (measurable outcomes)?
3. Does it specify COUNTS for migrations/renames/rebrands ("4 endpoints",
   "12 occurrences"), or just "the migration" / "rename everything"?
4. Does it include VERIFICATION commands or expected outputs?

Return ONLY compact JSON, no prose:
{"complete": true|false,
 "warnings": ["red flag 1", "red flag 2", ...],
 "verdict": "exhaustive"|"partial"|"vague",
 "needs_exhaustive_prompt": true|false}

"exhaustive": all 4 criteria met, warnings empty.
"partial":    1-2 criteria missing, warnings list them.
"vague":      3-4 criteria missing, recommend /exhaustive-prompt.
SYS
)

OUTPUT=$(jq -c -n \
  --arg system "$SYSTEM_PROMPT" \
  --arg user "$AGENT_PROMPT_TRIMMED" \
  '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      type: "prompt",
      model: "claude-haiku-4-5",
      system: $system,
      prompt: $user,
      max_tokens: 400,
      response_format: "json",
      decision: "advisory",
      label: "completeness-check-llm"
    }
  }' 2>/dev/null || true)

[ -z "$OUTPUT" ] && exit 0

printf '%s\n' "$OUTPUT"
exit 0
