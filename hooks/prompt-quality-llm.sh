#!/usr/bin/env bash
# SCOPE: cos
# PreToolUse hook: Prompt Quality (LLM-evaluated, ADR-022)
# Fires on "Agent" tool use — emits a type:"prompt" handler that asks Haiku
# to score the agent prompt on 5 dimensions (specificity, actionability,
# context, measurability, scope). Advisory only — never blocks.
#
# Graceful degradation: if jq is missing, Claude Code can't run prompt-type
# hooks, or stdin is empty/invalid, the hook exits 0 and emits nothing.
#
# This is the Claude Code adapter for the legacy regex-based prompt-quality.sh.
# Both hooks may run in parallel during the migration window (see ADR-022).

set -uo pipefail

_HOOK_NAME="prompt-quality-llm"

# Source common helpers if present (capability gating, private mode)
_LIB_DIR="$(dirname "$0")/_lib"
[ -f "$_LIB_DIR/common.sh" ] && source "$_LIB_DIR/common.sh"

# Capability/private-mode gating — only enforce if helpers are loaded
if type check_capability_level &>/dev/null; then
  check_capability_level "prompt-quality-llm"
fi
if type check_private_mode &>/dev/null; then
  check_private_mode
fi

# Read stdin (JSON with tool_name, tool_input)
INPUT=$(cat 2>/dev/null || true)
[ -z "$INPUT" ] && exit 0

# jq is required to parse the input safely. Without it, degrade silently.
command -v jq &>/dev/null || exit 0

# Only process Agent tool dispatch
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
[ "$TOOL_NAME" != "Agent" ] && exit 0

# Extract agent prompt/description
AGENT_PROMPT=$(echo "$INPUT" | jq -r '
  .tool_input.prompt // .tool_input.description // ""
' 2>/dev/null || true)

[ -z "$AGENT_PROMPT" ] || [ "$AGENT_PROMPT" = "null" ] && exit 0

# Truncate the user prompt to keep the Haiku call cheap and fast.
AGENT_PROMPT_TRIMMED=$(printf '%s' "$AGENT_PROMPT" | head -c 4000)

SYSTEM_PROMPT=$(cat <<'SYS'
You are a prompt-quality reviewer for a multi-agent orchestration system.
Score the user-provided agent prompt on 5 dimensions, each 0-20:

(a) specificity   — concrete file paths, function names, line ranges
(b) actionability — clear action verb + target
(c) context       — background, constraints, prior decisions
(d) measurability — verification commands, expected outputs, acceptance criteria
(e) scope         — bounded scope (counts/lists), not unbounded ("everything")

Return ONLY compact JSON, no prose:
{"score": <0-100>, "specificity": <0-20>, "actionability": <0-20>,
 "context": <0-20>, "measurability": <0-20>, "scope": <0-20>,
 "verdict": "low"|"medium"|"high",
 "suggestions": ["short bullet", ...]}

Use "low" for total < 30, "medium" for 30-69, "high" for >= 70.
Suggestions array MUST be empty when verdict is "high".
SYS
)

# Build the prompt-type hook output. Claude Code routes the body of the
# "prompt" key to the configured fast model (Haiku by default) and surfaces
# the response as advisory context.
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
      label: "prompt-quality-llm"
    }
  }' 2>/dev/null || true)

# If jq failed for any reason, degrade to silent no-op — never block.
[ -z "$OUTPUT" ] && exit 0

printf '%s\n' "$OUTPUT"
exit 0
