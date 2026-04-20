#!/usr/bin/env bash
# PreToolUse hook: Adaptive Bypass — Automatic Complexity Classification
# Fires on "Agent" tool use — classifies task complexity and recommends workflow
# Advisory only (exit 0) — does NOT block, injects classification for the model
# Must complete in <100ms
#
# PURPOSE: Automatically measures task complexity from prompt signals and injects
# a classification so the orchestrator can choose the appropriate workflow level.
# Replaces manual complexity guessing with data-driven estimation.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="adaptive-bypass"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Future-proof: auto-disabled at higher capability levels
# Note: check_capability_level calls exit 0 internally if the component is disabled.
# Do NOT use `&& exit 0` pattern — in bash, a failed if-block with no else returns 0,
# which would cause false-positive early exit.
check_capability_level "adaptive-bypass"

# Skip if private mode
check_private_mode

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR=$(_resolve_metrics_dir)
BYPASS_LOG="$METRICS_DIR/adaptive-bypass.jsonl"

# Read stdin (JSON with tool_name, tool_input)
INPUT=$(cat)

# Exit early if no input
if [ -z "$INPUT" ]; then
  exit 0
fi

# Require jq
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Only process Agent/task/delegate tool calls
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
case "$TOOL_NAME" in
  Agent|task|delegate) ;;
  *) exit 0 ;;
esac

# Extract agent prompt/description
AGENT_PROMPT=$(echo "$INPUT" | jq -r '
  .tool_input.prompt // .tool_input.description // ""
' 2>/dev/null)

if [ -z "$AGENT_PROMPT" ] || [ "$AGENT_PROMPT" = "null" ]; then
  exit 0
fi

# --- Read project phase ---
PHASE=$(get_phase "reconstruction")

# --- Complexity scoring ---
SCORE=0

# 1. File paths mentioned (+1 per unique path)
FILE_PATH_COUNT=$(echo "$AGENT_PROMPT" | grep -oiE '[a-zA-Z0-9_./-]+\.(go|ts|py|js|yaml|yml|json|md|sh|jsx|tsx|css|sql|proto|toml|rs|java|rb|php|swift|kt)' | sort -u | wc -l | tr -d ' ')
SCORE=$((SCORE + FILE_PATH_COUNT))

# 2. Directory references (+5 per dir)
DIR_COUNT=$(echo "$AGENT_PROMPT" | grep -oE '(src|internal|pkg|lib|cmd|hooks|rules|skills|tests|services|api|domain|application|infrastructure|components|modules|pages|routes)/[a-zA-Z0-9_/-]*' | sort -u | wc -l | tr -d ' ')
SCORE=$((SCORE + DIR_COUNT * 5))

# 3. Scope escalation words: "all", "every", "entire" (+20)
if echo "$AGENT_PROMPT" | grep -qiE '\b(all files|all services|every endpoint|every service|every file|entire codebase|entire project|all endpoints|all controllers|all repositories|every module|all modules)\b'; then
  SCORE=$((SCORE + 20))
fi

# 4. Bulk operation words: "migrate", "rebrand", "refactor" (+15)
if echo "$AGENT_PROMPT" | grep -qiE '\b(migrate|rebrand|refactor|rename everywhere|replace all|bulk update|mass rename|global replace|find and replace|mass migration)\b'; then
  SCORE=$((SCORE + 15))
fi

# 5. Multi-service keywords (+25)
if echo "$AGENT_PROMPT" | grep -qiE '\b(all services|across services|across the project|cross-service|every service|multi-service|all packages|across all)\b'; then
  SCORE=$((SCORE + 25))
fi

# 6. Security/auth keywords (+30)
if echo "$AGENT_PROMPT" | grep -qiE '\b(auth|authentication|authorization|jwt|oauth|payment|credential|secret|encrypt|decrypt|certificate|rbac|acl|permission system|api.?key|password|security review)\b'; then
  SCORE=$((SCORE + 30))
fi

# 7. Explicit count in prompt — use that count if higher
EXPLICIT_COUNT=$(echo "$AGENT_PROMPT" | grep -oE '[0-9]+[[:space:]]*(files?|endpoints?|services?|modules?|components?|controllers?|routes?)' | grep -oE '[0-9]+' | sort -rn | head -1)
if [ -n "$EXPLICIT_COUNT" ] && [ "$EXPLICIT_COUNT" -gt "$SCORE" ]; then
  SCORE=$EXPLICIT_COUNT
fi

# 8. Short prompt likely trivial — if <100 chars and no other signals, keep low
PROMPT_LENGTH=${#AGENT_PROMPT}
# (no additional points — short prompts just don't accumulate signals)

# --- Phase modifier ---
PHASE_SHIFT=0
case "$PHASE" in
  reconstruction)
    PHASE_SHIFT=10  # shift thresholds UP (more things are trivial)
    ;;
  stabilization)
    PHASE_SHIFT=0   # no shift
    ;;
  production)
    PHASE_SHIFT=-5  # shift thresholds DOWN (more things need governance)
    ;;
  maintenance)
    PHASE_SHIFT=-5  # shift thresholds DOWN
    ;;
esac

# Apply phase shift to thresholds
TRIVIAL_MAX=$((5 + PHASE_SHIFT))
SMALL_MAX=$((15 + PHASE_SHIFT))
MEDIUM_MAX=$((40 + PHASE_SHIFT))
LARGE_MAX=$((80 + PHASE_SHIFT))

# Ensure minimums make sense
[ "$TRIVIAL_MAX" -lt 1 ] && TRIVIAL_MAX=1
[ "$SMALL_MAX" -lt 5 ] && SMALL_MAX=5
[ "$MEDIUM_MAX" -lt 15 ] && MEDIUM_MAX=15
[ "$LARGE_MAX" -lt 30 ] && LARGE_MAX=30

# --- Classification ---
COMPLEXITY=""
RECOMMENDATION=""

if [ "$SCORE" -le "$TRIVIAL_MAX" ]; then
  COMPLEXITY="TRIVIAL"
  RECOMMENDATION="Do directly, no delegation needed"
elif [ "$SCORE" -le "$SMALL_MAX" ]; then
  COMPLEXITY="SMALL"
  RECOMMENDATION="Delegate if beneficial"
elif [ "$SCORE" -le "$MEDIUM_MAX" ]; then
  COMPLEXITY="MEDIUM"
  RECOMMENDATION="Plan first recommended (/plan-feature or /plan-bug)"
elif [ "$SCORE" -le "$LARGE_MAX" ]; then
  COMPLEXITY="LARGE"
  RECOMMENDATION="SDD pipeline recommended (/sdd-new)"
else
  COMPLEXITY="CRITICAL"
  RECOMMENDATION="SDD + security review required (/sdd-new with security gates)"
fi

# --- Logging ---
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mkdir -p "$METRICS_DIR" 2>/dev/null

ENTRY=$(jq -c -n \
  --arg ts "$TIMESTAMP" \
  --arg complexity "$COMPLEXITY" \
  --argjson score "$SCORE" \
  --arg phase "$PHASE" \
  --argjson prompt_length "$PROMPT_LENGTH" \
  '{timestamp: $ts, complexity: $complexity, score: $score, phase: $phase, prompt_length: $prompt_length}')
safe_jsonl_append "$BYPASS_LOG" "$ENTRY"

# --- Output (injected into model context) ---
echo ""
echo "ADAPTIVE BYPASS: COMPLEXITY=$COMPLEXITY (score=$SCORE, phase=$PHASE)"
echo "Recommendation: $RECOMMENDATION"
echo ""

# Advisory only — always exit 0
exit 0
