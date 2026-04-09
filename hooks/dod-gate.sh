#!/usr/bin/env bash
# DEPRECATED: This hook's functionality is merged into completion-gate.sh (Phase 2).
# Do NOT wire this hook — it would duplicate the DoD check already in completion-gate.
# Original: PostToolUse hook: Definition of Done Gate
# Fires on "Agent" completions — checks DoD criteria based on task complexity.
# Blocks (exit 2) in production/maintenance if DoD not met; warns otherwise.

set -uo pipefail

_HOOK_NAME="dod-gate"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode
read_stdin_json

TOOL_OUTPUT=$(stdin_field '.tool_response.content' '')
if [ -z "$TOOL_OUTPUT" ]; then
  TOOL_OUTPUT=$(stdin_field '.tool_response' '' | jq -r 'if type == "array" then .[].text // "" else . // "" end' 2>/dev/null || true)
fi

METRICS_DIR=$(_resolve_metrics_dir)
PHASE=$(get_phase)
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Extract complexity from output
COMPLEXITY="unknown"
if echo "$TOOL_OUTPUT" | grep -qiE 'Complexity:\s*(trivial|small|medium|large|critical)'; then
  COMPLEXITY=$(echo "$TOOL_OUTPUT" | grep -iE 'Complexity:' | head -1 \
    | sed -E 's/.*Complexity:[[:space:]]*//' | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')
fi

[ "$COMPLEXITY" = "unknown" ] && exit 0

# Check DoD markers per complexity
DOD_MET=true
MISSING=""

check_marker() {
  local pattern="$1"
  local label="$2"
  if ! echo "$TOOL_OUTPUT" | grep -qiE "$pattern"; then
    DOD_MET=false
    MISSING="$MISSING $label"
  fi
}

case "$COMPLEXITY" in
  trivial)
    check_marker '(build|compile|go build|yarn build|npm run build).*0|exits 0|OK' 'code_compiles'
    ;;
  small)
    check_marker '(test|jest|pytest|go test).*pass' 'unit_tests_pass'
    ;;
  medium|large|critical)
    check_marker '(test.*added|_test\.|\.spec\.)' 'unit_tests_added'
    check_marker '(coverage|lint.*clean|no lint)' 'coverage_or_lint'
    if [ "$COMPLEXITY" = "large" ] || [ "$COMPLEXITY" = "critical" ]; then
      check_marker '(BLOCKER|CONCERN|SUGGESTION)' 'adversarial_review'
    fi
    ;;
esac

# Log result
safe_jsonl_append "$METRICS_DIR/dod-checks.jsonl" \
  "{\"timestamp\":\"$TIMESTAMP\",\"complexity\":\"$COMPLEXITY\",\"phase\":\"$PHASE\",\"dod_met\":$DOD_MET,\"missing\":\"${MISSING# }\"}"

if [ "$DOD_MET" = "false" ]; then
  MSG="DOD-GATE: Definition of Done not met for $COMPLEXITY task. Missing:$MISSING"
  echo "$MSG" >&2
  case "$PHASE" in
    production|maintenance)
      exit 2
      ;;
    *)
      exit 0
      ;;
  esac
fi

exit 0
