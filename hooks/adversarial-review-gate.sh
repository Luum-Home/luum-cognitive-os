#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: quality, verification, adversarial-review
# PostToolUse hook on Agent — enforces rules/adversarial-review.md.
# "Every review MUST produce at least one finding. 'Looks good' is prohibited."
# Fail-silent gate: emits warnings, never blocks (exit 0 always).

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="adversarial-review-gate"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"
[ -f "$(dirname "$0")/_lib/primitive-intervention.sh" ] && source "$(dirname "$0")/_lib/primitive-intervention.sh"

check_capability_level "adversarial-review-gate"
check_disabled_env "adversarial-review-gate"

read_stdin_json
INPUT="$_STDIN_JSON"
require_tool "Agent" "task" "delegate"

PROJECT_DIR="$_PROJECT_DIR"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
LOG_FILE="$METRICS_DIR/adversarial-review-gate.jsonl"

AGENT_OUTPUT=$(echo "$INPUT" | jq -r '.tool_result // .output // empty' 2>/dev/null)
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input // empty' 2>/dev/null)

if [[ -z "$AGENT_OUTPUT" ]]; then
  exit 0
fi

COMBINED_HAYSTACK="${TOOL_INPUT} ${AGENT_OUTPUT}"
IS_REVIEW=false
if echo "$COMBINED_HAYSTACK" | grep -qiE '(\breview\b|\baudit\b|\bverify\b|\bcritique\b|sdd-verify|code review|adversarial|self-review|pr-review)'; then
  IS_REVIEW=true
fi

if [[ "$IS_REVIEW" == "false" ]]; then
  exit 0
fi

HAS_FINDING=false
if echo "$AGENT_OUTPUT" | grep -qiE '(\bCRITICAL\b|\bHIGH\b|\bMEDIUM\b|\bLOW\b|severity:|finding:|issue:|problem:|concern:|\brisk:|\bbug:|\bgap:)'; then
  HAS_FINDING=true
fi

HAS_PROHIBITED_PHRASE=false
if echo "$AGENT_OUTPUT" | grep -qiE '(looks good|no issues found|nothing to flag|\blgtm\b|all good|no findings|no problems found)'; then
  HAS_PROHIBITED_PHRASE=true
fi

mkdir -p "$METRICS_DIR"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [[ "$HAS_FINDING" == "false" ]]; then
  if [[ "$HAS_PROHIBITED_PHRASE" == "true" ]]; then
    echo ""
    echo "WARNING [adversarial-review-gate]: Review closed with prohibited phrase ('looks good' / 'no issues found') and ZERO findings."
    echo "Rule: rules/adversarial-review.md — every review MUST produce at least one finding (CRITICAL/HIGH/MEDIUM/LOW)."
    echo "Re-run with adversarial framing: assume the code IS broken, then prove it is not."
    echo ""
    SEVERITY="prohibited_phrase_no_findings"
  else
    echo ""
    echo "WARNING [adversarial-review-gate]: Review output contains no findings with severity."
    echo "Rule: rules/adversarial-review.md — every review MUST surface at least one finding."
    echo ""
    SEVERITY="no_findings"
  fi
  ENTRY=$(jq -n \
    --arg ts "$TIMESTAMP" \
    --arg sev "$SEVERITY" \
    --arg prohibited "$HAS_PROHIBITED_PHRASE" \
    '{timestamp:$ts, hook:"adversarial-review-gate", severity:$sev, prohibited_phrase:($prohibited=="true"), has_finding:false}')
  safe_jsonl_append "$LOG_FILE" "$ENTRY"
  if type primitive_intervention_emit >/dev/null 2>&1; then
    primitive_intervention_emit "adversarial-review-gate" "hooks/adversarial-review-gate.sh" "warn" "$SEVERITY" "agent-output" ".cognitive-os/metrics/adversarial-review-gate.jsonl" "Agent" || true
  fi
else
  ENTRY=$(jq -n \
    --arg ts "$TIMESTAMP" \
    '{timestamp:$ts, hook:"adversarial-review-gate", severity:"pass", has_finding:true}')
  safe_jsonl_append "$LOG_FILE" "$ENTRY"
fi

exit 0
