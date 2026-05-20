#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: quality, verification, metrics
# PostToolUse hook on Agent — validates Trust Report presence and logs trust scores.
# Checks agent output for Trust Report, extracts score, logs to metrics.

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="trust-score-validator"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"
[ -f "$(dirname "$0")/_lib/primitive-intervention.sh" ] && source "$(dirname "$0")/_lib/primitive-intervention.sh"

# Auto-disabled at capability level 5
check_capability_level "trust-score-validator"
# Runtime disable: DISABLE_HOOK_TRUST_SCORE_VALIDATOR=true skips this hook for the session
check_disabled_env "trust-score-validator"

# Read stdin and gate on Agent/task/delegate tool
read_stdin_json
INPUT="$_STDIN_JSON"
require_tool "Agent" "task" "delegate"

PROJECT_DIR="$_PROJECT_DIR"
COGNITIVE_OS_DIR="$PROJECT_DIR/.cognitive-os"
METRICS_DIR="$COGNITIVE_OS_DIR/metrics"
TRUST_LOG="$METRICS_DIR/trust-scores.jsonl"

# Get agent output
AGENT_OUTPUT=$(echo "$INPUT" | jq -r '.tool_result // .output // empty' 2>/dev/null)
if [[ -z "$AGENT_OUTPUT" ]]; then
  exit 0
fi

PARSE_RESULT=$(AGENT_OUTPUT="$AGENT_OUTPUT" PYTHONPATH="$PROJECT_DIR:${PYTHONPATH:-}" python3 - <<'PY'
import json
import os
import sys

from lib.trust_report_parser import TrustReportParseError, TrustReportParser

text = os.environ.get("AGENT_OUTPUT", "")
has_structured_marker = "TRUST_REPORT:" in text.upper()
has_legacy_marker = "TRUST REPORT:" in text.upper()
has_score_marker = "SCORE:" in text.upper()
try:
    report = TrustReportParser().extract_from_output(text)
    if report is None and has_score_marker:
        report = TrustReportParser().parse(text)
except TrustReportParseError as exc:
    print(json.dumps({
        "state": "malformed",
        "error": str(exc),
        "hint": exc.hint,
    }))
    sys.exit(0)

if report is None:
    if has_structured_marker or has_legacy_marker:
        print(json.dumps({
            "state": "malformed",
            "error": "Trust report marker found, but no parseable trust score block was present.",
            "hint": "Use: TRUST_REPORT: SCORE=<0-100> STATUS=<HIGH|MEDIUM|LOW|CRITICAL> EVIDENCE=<N> UNCERTAINTIES=<N>",
        }))
    else:
        print(json.dumps({"state": "missing"}))
    sys.exit(0)

fmt = "structured" if has_structured_marker else "legacy"
print(json.dumps({
    "state": "ok",
    "format": fmt,
    "score": report.score,
    "status": report.status,
    "evidence_count": report.evidence_count,
    "uncertainty_count": report.uncertainty_count,
}))
PY
)

PARSE_STATE=$(echo "$PARSE_RESULT" | jq -r '.state // "missing"' 2>/dev/null || echo "missing")

if [[ "$PARSE_STATE" == "missing" ]]; then
  echo ""
  echo "WARNING: Agent did not provide Trust Report. Confidence cannot be assessed."
  echo "Agents MUST include a Trust Report with score, evidence, uncertainties, and human verification steps."
  echo ""
  if type primitive_intervention_emit >/dev/null 2>&1; then
    primitive_intervention_emit "trust-score-validator" "hooks/trust-score-validator.sh" "warn" "trust_report_missing" "agent-output" ".cognitive-os/metrics/trust-scores.jsonl" "Agent" || true
  fi
  exit 0
fi

if [[ "$PARSE_STATE" == "malformed" ]]; then
  PARSE_ERROR=$(echo "$PARSE_RESULT" | jq -r '.error // "malformed trust report"' 2>/dev/null || echo "malformed trust report")
  PARSE_HINT=$(echo "$PARSE_RESULT" | jq -r '.hint // empty' 2>/dev/null || true)
  echo ""
  echo "TRUST_SCORE_VALIDATOR: BLOCKED — malformed Trust Report."
  echo "$PARSE_ERROR"
  if [[ -n "$PARSE_HINT" ]]; then
    echo "Hint: $PARSE_HINT"
  fi
  echo ""
  if type primitive_intervention_emit >/dev/null 2>&1; then
    primitive_intervention_emit "trust-score-validator" "hooks/trust-score-validator.sh" "block" "trust_report_malformed" "agent-output" ".cognitive-os/metrics/trust-scores.jsonl" "Agent" || true
  fi
  exit 2
fi

SCORE=$(echo "$PARSE_RESULT" | jq -r '.score' 2>/dev/null)
STATUS=$(echo "$PARSE_RESULT" | jq -r '.status' 2>/dev/null)
EVIDENCE_COUNT=$(echo "$PARSE_RESULT" | jq -r '.evidence_count' 2>/dev/null)
UNCERTAINTY_COUNT=$(echo "$PARSE_RESULT" | jq -r '.uncertainty_count' 2>/dev/null)
REPORT_FORMAT=$(echo "$PARSE_RESULT" | jq -r '.format' 2>/dev/null)

# Ensure metrics directory exists
mkdir -p "$METRICS_DIR"

# Extract agent name if available
AGENT_NAME=$(echo "$INPUT" | jq -r '.agent_name // .tool_input.prompt // "unknown"' 2>/dev/null | head -c 100)

# Log to metrics
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
AGENT_JSON=$(printf '%s' "$AGENT_NAME" | jq -Rs '.')
ENTRY="{\"timestamp\":\"$TIMESTAMP\",\"agent\":$AGENT_JSON,\"score\":$SCORE,\"status\":\"$STATUS\",\"format\":\"$REPORT_FORMAT\",\"evidence_count\":$EVIDENCE_COUNT,\"uncertainty_count\":$UNCERTAINTY_COUNT}"
safe_jsonl_append "$TRUST_LOG" "$ENTRY"

if [[ "$REPORT_FORMAT" == "legacy" ]]; then
  echo ""
  echo "WARNING: Legacy Trust Report format accepted for compatibility. New agents MUST emit the ADR-038 TRUST_REPORT header."
  echo ""
fi

# Alert on low confidence
if [[ "$SCORE" -lt 50 ]]; then
  echo ""
  echo "ALERT: Low confidence result (Trust Score: $SCORE/100). Human review strongly recommended."
  echo "The agent reported low confidence in its work. Please verify the output carefully."
  echo ""
elif [[ "$SCORE" -lt 70 ]]; then
  echo ""
  echo "NOTE: Medium-low confidence (Trust Score: $SCORE/100). Spot-check recommended."
  echo ""
fi

exit 0
