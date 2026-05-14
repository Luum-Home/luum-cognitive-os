#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: quality, verification, decision-depth
# PostToolUse hook on Agent — enforces rules/decision-depth-gate.md.
# "Before closing a finding with 'I'll document the difference', the agent MUST
#  investigate the underlying invariant."
# Fail-silent gate: emits warnings, never blocks (exit 0 always).

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="decision-depth-gate"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"
[ -f "$(dirname "$0")/_lib/primitive-intervention.sh" ] && source "$(dirname "$0")/_lib/primitive-intervention.sh"

check_capability_level "decision-depth-gate"
check_disabled_env "decision-depth-gate"

read_stdin_json
INPUT="$_STDIN_JSON"
require_tool "Agent" "task" "delegate"

PROJECT_DIR="$_PROJECT_DIR"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
LOG_FILE="$METRICS_DIR/decision-depth-gate.jsonl"

AGENT_OUTPUT=$(echo "$INPUT" | jq -r '.tool_result // .output // empty' 2>/dev/null)
if [[ -z "$AGENT_OUTPUT" ]]; then
  exit 0
fi

HAS_FINDING_CONTEXT=false
if echo "$AGENT_OUTPUT" | grep -qiE '(\bfinding\b|inconsistency|inconsistencies|duplication|ambiguity|discrepancy|divergence|mismatch)'; then
  HAS_FINDING_CONTEXT=true
fi

if [[ "$HAS_FINDING_CONTEXT" == "false" ]]; then
  exit 0
fi

HAS_DOC_RESOLUTION=false
if echo "$AGENT_OUTPUT" | grep -qiE "(i'll document this|i will document this|voy a documentarlo|intentionally different|by design|document the difference|add a comment explaining|just document|note this difference|leave a note)"; then
  HAS_DOC_RESOLUTION=true
fi

if [[ "$HAS_DOC_RESOLUTION" == "false" ]]; then
  exit 0
fi

HAS_INVESTIGATION=false
if echo "$AGENT_OUTPUT" | grep -qiE '(\bbecause\b|the relationship is|verified that|checked that|confirmed that|the invariant holds|root cause|underlying reason|traced (it )?to|invariant:)'; then
  HAS_INVESTIGATION=true
fi

mkdir -p "$METRICS_DIR"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [[ "$HAS_INVESTIGATION" == "false" ]]; then
  echo ""
  echo "WARNING [decision-depth-gate]: Closing a finding by documentation without investigating the underlying invariant."
  echo "Rule: rules/decision-depth-gate.md — before resolving with 'I'll document the difference', verify the relationship."
  echo "Ask: Why does this divergence exist? What invariant connects these? Did I trace it to root?"
  echo ""
  ENTRY=$(jq -n \
    --arg ts "$TIMESTAMP" \
    '{timestamp:$ts, hook:"decision-depth-gate", severity:"shallow_resolution", doc_resolution:true, investigated:false}')
  safe_jsonl_append "$LOG_FILE" "$ENTRY"
  if type primitive_intervention_emit >/dev/null 2>&1; then
    primitive_intervention_emit "decision-depth-gate" "hooks/decision-depth-gate.sh" "warn" "shallow_resolution" "agent-output" ".cognitive-os/metrics/decision-depth-gate.jsonl" "Agent" || true
  fi
else
  ENTRY=$(jq -n \
    --arg ts "$TIMESTAMP" \
    '{timestamp:$ts, hook:"decision-depth-gate", severity:"pass", doc_resolution:true, investigated:true}')
  safe_jsonl_append "$LOG_FILE" "$ENTRY"
fi

exit 0
