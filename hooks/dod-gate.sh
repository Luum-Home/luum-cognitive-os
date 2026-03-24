#!/usr/bin/env bash
# PostToolUse hook: Definition of Done Gate
# Fires on "Agent" tool use — checks DoD criteria on task completion
# Must complete in <5 seconds
#
# When an agent reports completion, this hook checks if the assigned
# complexity level's DoD criteria have been met based on output evidence.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
PHASE_DEFAULT="reconstruction"

# Read stdin (JSON with tool_name, tool_input, tool_response)
INPUT=$(cat)

# Exit early if no input
if [ -z "$INPUT" ]; then
  exit 0
fi

# Require jq
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Only process Agent tool
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [ "$TOOL_NAME" != "Agent" ]; then
  exit 0
fi

# Get response text
RESPONSE=$(echo "$INPUT" | jq -r '.tool_response // empty' 2>/dev/null)
if [ -z "$RESPONSE" ]; then
  exit 0
fi

# Check if this looks like a completion report
COMPLETION_SIGNALS="done|complete|finished|implemented|fixed|resolved|delivered|all tasks|PASS"
if ! echo "$RESPONSE" | grep -qiE "$COMPLETION_SIGNALS"; then
  exit 0
fi

# Detect complexity level from agent output
COMPLEXITY=""
if echo "$RESPONSE" | grep -qiE "complexity:\s*(trivial|Trivial|TRIVIAL)"; then
  COMPLEXITY="trivial"
elif echo "$RESPONSE" | grep -qiE "complexity:\s*(small|Small|SMALL)"; then
  COMPLEXITY="small"
elif echo "$RESPONSE" | grep -qiE "complexity:\s*(medium|Medium|MEDIUM)"; then
  COMPLEXITY="medium"
elif echo "$RESPONSE" | grep -qiE "complexity:\s*(large|Large|LARGE)"; then
  COMPLEXITY="large"
elif echo "$RESPONSE" | grep -qiE "complexity:\s*(critical|Critical|CRITICAL)"; then
  COMPLEXITY="critical"
fi

# If no complexity declared, try to infer from output size and signals
if [ -z "$COMPLEXITY" ]; then
  # Check for security/payment/auth signals -> critical
  if echo "$RESPONSE" | grep -qiE "security|payment|migration|auth.change|encrypt"; then
    COMPLEXITY="critical"
  # Check for multi-service signals -> large
  elif echo "$RESPONSE" | grep -qiE "multi-service|cross-service|integration.test|sdk.package"; then
    COMPLEXITY="large"
  # Check for new feature signals -> medium
  elif echo "$RESPONSE" | grep -qiE "new feature|new endpoint|new use.case|refactor"; then
    COMPLEXITY="medium"
  else
    # Default: no DoD gate for unclassified tasks (let it pass)
    exit 0
  fi
fi

# Get current phase
PHASE="$PHASE_DEFAULT"
if [ -f "$CONFIG_FILE" ] && command -v grep &>/dev/null; then
  DETECTED_PHASE=$(grep -E '^\s+phase:' "$CONFIG_FILE" | head -1 | sed 's/.*phase:\s*//' | sed 's/\s*#.*//' | tr -d '[:space:]')
  if [ -n "$DETECTED_PHASE" ]; then
    PHASE="$DETECTED_PHASE"
  fi
fi

# Determine enforcement level based on phase
ENFORCEMENT="WARN"
if [ "$PHASE" = "production" ] || [ "$PHASE" = "maintenance" ]; then
  ENFORCEMENT="BLOCK"
fi

# Check DoD criteria based on complexity level
MISSING=""
CHECKED=0
PASSED=0

check_criterion() {
  local name="$1"
  local pattern="$2"
  CHECKED=$((CHECKED + 1))
  if echo "$RESPONSE" | grep -qiE "$pattern"; then
    PASSED=$((PASSED + 1))
  else
    if [ -z "$MISSING" ]; then
      MISSING="$name"
    else
      MISSING="$MISSING, $name"
    fi
  fi
}

case "$COMPLEXITY" in
  trivial)
    check_criterion "code_compiles" "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"
    check_criterion "no_lint_errors" "lint.*clean|lint.*pass|no.lint|0 issues|0 errors"
    ;;
  small)
    check_criterion "code_compiles" "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"
    check_criterion "unit_tests_pass" "tests? pass|PASS|all tests|test.*success|0 failed"
    check_criterion "no_lint_errors" "lint.*clean|lint.*pass|no.lint|0 issues|0 errors"
    ;;
  medium)
    check_criterion "code_compiles" "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"
    check_criterion "unit_tests_added" "new test|added test|test file|_test\.go|\.spec\.ts|test coverage"
    check_criterion "coverage_maintained" "coverage|cover.*[0-9]+%"
    check_criterion "lint_clean" "lint.*clean|lint.*pass|no.lint|0 issues|0 errors"
    check_criterion "docs_updated" "doc.*updated|README|\.md.*modified|documentation"
    ;;
  large)
    check_criterion "readiness_check_pass" "readiness.*pass|readiness.*PASS|prerequisites.*met"
    check_criterion "code_compiles" "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"
    check_criterion "unit_tests_80_percent" "coverage.*[8-9][0-9]%|coverage.*100%|80%|>= 80"
    check_criterion "integration_tests" "integration.*test|integration.*pass|e2e.*pass"
    check_criterion "architecture_compliance" "architecture.*compliance|no.*violation|ginext|clean.arch"
    check_criterion "docs_updated" "doc.*updated|README|\.md.*modified|documentation"
    check_criterion "adversarial_review" "BLOCKER|CONCERN|SUGGESTION|adversarial.*review"
    ;;
  critical)
    check_criterion "readiness_check_pass" "readiness.*pass|readiness.*PASS|prerequisites.*met"
    check_criterion "code_compiles" "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"
    check_criterion "unit_tests_80_percent" "coverage.*[8-9][0-9]%|coverage.*100%|80%|>= 80"
    check_criterion "integration_tests" "integration.*test|integration.*pass|e2e.*pass"
    check_criterion "architecture_compliance" "architecture.*compliance|no.*violation|ginext|clean.arch"
    check_criterion "docs_updated" "doc.*updated|README|\.md.*modified|documentation"
    check_criterion "adversarial_review" "BLOCKER|CONCERN|SUGGESTION|adversarial.*review"
    check_criterion "security_review" "security.*review|security.*assessment|vulnerability|threat"
    check_criterion "idempotency_verified" "idempoten|transaction.id|dedup|deduplicat"
    check_criterion "audit_trail_present" "audit.*trail|audit.*log|who.*when.*what|traceable"
    check_criterion "rollback_tested" "rollback.*test|rollback.*plan|rollback.*procedure|revert"
    ;;
esac

# Report results
if [ -n "$MISSING" ]; then
  cat <<EOF

---
## DoD Gate: $ENFORCEMENT — Complexity: $COMPLEXITY ($PASSED/$CHECKED criteria met)

**Missing DoD criteria**: $MISSING

The agent reported completion at **$COMPLEXITY** complexity but the following Definition of Done criteria were not evidenced in the output:

$(IFS=','; for item in $MISSING; do echo "- **$(echo "$item" | tr -d ' ')**"; done)

### Required Action
EOF

  if [ "$ENFORCEMENT" = "BLOCK" ]; then
    cat <<EOF
**BLOCKED**: Phase is \`$PHASE\`. Task CANNOT be marked as done until all criteria pass.
The agent must address the missing criteria before completion is accepted.
EOF
  else
    cat <<EOF
**WARNING**: Phase is \`$PHASE\`. Missing criteria noted but not blocking.
Consider addressing these items for quality assurance.
Run \`/dod-check\` for detailed verification.
EOF
  fi
fi

exit 0
