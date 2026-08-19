#!/usr/bin/env bash
# SCOPE: os-only
# PostToolUse hook: Skill Feedback Tracker
# Fires on "Agent" completions — tracks skill success/failure rates.
# Warns when a skill has degraded (3+ failures).

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="skill-feedback-tracker"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode
read_stdin_json

TOOL_PROMPT=$(stdin_field '.tool_input.prompt' '')
TOOL_OUTPUT=$(stdin_field '.tool_response.content' '')
if [ -z "$TOOL_OUTPUT" ]; then
  TOOL_OUTPUT=$(stdin_field '.tool_response' '' | jq -r 'if type == "array" then .[].text // "" else . // "" end' 2>/dev/null || true)
fi

# --- Extract skill name -----------------------------------------------------
# The `skill` field of this file is read back as a skill identifier by
# cos_lib/skill_failure_repair.py (emits repair signals), by
# cos_lib/consumer_improvement_proposals.py (emits "Review degraded skill
# <name>" proposals) and by cos_lib/skill_lifecycle_promoter.py, so only a
# real skill identifier may land in it.
#
# Until this fix the fallback was `grep -oE '/[a-z][a-z0-9-]+' | head -1`,
# which took the first lowercase path segment found anywhere in the agent
# prompt. Measured over the 200 rows written before the fix, that produced
# ZERO rows naming a skill that exists: the operator home directory became a
# "skill" named after the username (131 rows, 65% of the stream),
# `/private/tmp/...` became "private" (15), and the byte class stops at the
# first non-ASCII byte so "despues" with an accent became "despu".
# Writing the username into telemetry also breaks
# rules/local-privacy-hygiene.md. Recount with
# scripts/audit_skill_telemetry_names.py.
# The `SKILL: Load` branch was no better: emitters write the path form
# (SKILL: Load `skills/foo/SKILL.md`), and `basename` on that yields
# "SKILL.md".
#
# Rule now: a candidate is only accepted if it resolves to a SKILL.md on
# disk. An Agent run that cannot be attributed to a skill writes no row --
# skill-feedback.jsonl is per-skill feedback, and a sentinel row here would
# be re-read by skill_failure_repair.py as a degraded skill of that name.
_skill_exists() {
  [ -n "${1:-}" ] || return 1
  [ -f "$_PROJECT_DIR/skills/$1/SKILL.md" ] && return 0
  [ -f "$_PROJECT_DIR/.cognitive-os/skills/cos/$1/SKILL.md" ] && return 0
  return 1
}

SKILL_NAME=""
SKILL_CANDIDATES=$(printf '%s' "$TOOL_PROMPT" \
  | grep -oE 'SKILL: Load `[^`]+`|skills/[a-z0-9][a-z0-9_-]*' 2>/dev/null \
  | sed -e 's/^SKILL: Load `//' -e 's/`$//' -e 's|/*SKILL\.md$||' -e 's|.*/||' \
  | head -10 || true)
while IFS= read -r _candidate; do
  [ -n "$_candidate" ] || continue
  if _skill_exists "$_candidate"; then
    SKILL_NAME="$_candidate"
    break
  fi
done <<EOF_SKILL_CANDIDATES
$SKILL_CANDIDATES
EOF_SKILL_CANDIDATES

[ -z "$SKILL_NAME" ] && exit 0

# Detect success or failure
SUCCESS=true
if echo "$TOOL_OUTPUT" | grep -qiE '(FAIL|ERROR|build failed|test failed|ESCALATION)'; then
  SUCCESS=false
fi

METRICS_DIR=$(_resolve_metrics_dir)
FEEDBACK_LOG="$METRICS_DIR/skill-feedback.jsonl"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

safe_jsonl_append "$FEEDBACK_LOG" \
  "{\"timestamp\":\"$TIMESTAMP\",\"skill\":\"$SKILL_NAME\",\"success\":$SUCCESS}"

# Count recent failures for this skill (last 24h)
if [ "$SUCCESS" = "false" ] && [ -f "$FEEDBACK_LOG" ]; then
  CUTOFF=$(( $(date +%s) - 86400 ))
  FAIL_COUNT=$(grep "\"skill\":\"$SKILL_NAME\"" "$FEEDBACK_LOG" 2>/dev/null \
    | grep '"success":false' | wc -l | tr -d ' ')
  if [ "${FAIL_COUNT:-0}" -ge 3 ]; then
    echo "SKILL DEGRADED: Skill '$SKILL_NAME' has failed ${FAIL_COUNT} times. Consider running /optimize-skill $SKILL_NAME" >&2
  fi
fi

exit 0
