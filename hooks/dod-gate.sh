#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: quality, definition-of-done, phase-aware
# DoD Gate Hook — PostToolUse for Agent
# Reads the agent RESULT block, infers task complexity (trivial/small/medium/
# large/critical), and checks the corresponding Definition of Done criteria
# from rules/definition-of-done.md. Advisory only — exits 0 always.
#
# Phase-aware enforcement label:
#   reconstruction / stabilization : WARN (proceed with caution)
#   production     / maintenance   : BLOCK (note only — never exits non-zero)
#
# Contract: described in rules/definition-of-done.md and rules/agent-quality.md.
# Related: completion-gate.sh performs the same check in a combined pipeline.
# This standalone hook exists for users that want DoD checks in isolation.
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="dod-gate"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/artifact-status.sh"

INPUT=$(cat)
[ -z "$INPUT" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[ "$TOOL_NAME" != "Agent" ] && exit 0

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
[ ! -f "$CONFIG_FILE" ] && CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"

METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  _SESSION_FILE="$PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  [ -f "$_SESSION_FILE" ] && SESSION_ID=$(cat "$_SESSION_FILE" 2>/dev/null)
fi
if [ -n "$SESSION_ID" ] && [ -d "$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID" ]; then
  METRICS_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/metrics"
fi
DOD_LOG="$METRICS_DIR/dod-gate.jsonl"

RESPONSE=$(echo "$INPUT" | jq -r '.tool_response.result // .tool_response.output // .tool_response.content // .tool_response // ""' 2>/dev/null)
[ -z "$RESPONSE" ] || [ "$RESPONSE" = "null" ] && exit 0

AGENT_PROMPT=$(echo "$INPUT" | jq -r '.tool_input.prompt // .tool_input.description // ""' 2>/dev/null)

# Only act on completion
IS_COMPLETION=false
echo "$RESPONSE" | grep -qiE "done|complete|finished|implemented|fixed|resolved|delivered|all tasks|PASS|listo" && IS_COMPLETION=true
[ "$IS_COMPLETION" = "true" ] || exit 0

# Resolve phase
PHASE="reconstruction"
if [ -f "$CONFIG_FILE" ]; then
  PARSED=$(grep -E '^\s*phase:' "$CONFIG_FILE" | head -1 | sed 's/.*phase:[[:space:]]*//' | sed 's/[[:space:]]*#.*//' | tr -d '[:space:]')
  [ -n "$PARSED" ] && PHASE="$PARSED"
fi

ENFORCEMENT="WARN"
case "$PHASE" in
  production|maintenance) ENFORCEMENT="BLOCK" ;;
esac

# Infer complexity: explicit marker first, then heuristic on response
COMPLEXITY=""
echo "$RESPONSE" | grep -qiE "complexity:[[:space:]]*trivial"  && COMPLEXITY="trivial"
echo "$RESPONSE" | grep -qiE "complexity:[[:space:]]*small"    && COMPLEXITY="small"
echo "$RESPONSE" | grep -qiE "complexity:[[:space:]]*medium"   && COMPLEXITY="medium"
echo "$RESPONSE" | grep -qiE "complexity:[[:space:]]*large"    && COMPLEXITY="large"
echo "$RESPONSE" | grep -qiE "complexity:[[:space:]]*critical" && COMPLEXITY="critical"
if [ -z "$COMPLEXITY" ]; then
  echo "$RESPONSE" | grep -qiE "security|payment|migration|auth.change|encrypt" && COMPLEXITY="critical"
  [ -z "$COMPLEXITY" ] && echo "$RESPONSE" | grep -qiE "multi-service|cross-service|integration.test|sdk.package" && COMPLEXITY="large"
  [ -z "$COMPLEXITY" ] && echo "$RESPONSE" | grep -qiE "new feature|new endpoint|new use.case|refactor" && COMPLEXITY="medium"
fi

# Unknown complexity: advisory note, exit
if [ -z "$COMPLEXITY" ]; then
  safe_jsonl_append "$DOD_LOG" "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"NO_COMPLEXITY\",\"phase\":\"$PHASE\"}"
  exit 0
fi

MISSING=""
CHECKED=0
PASSED=0
TEST_ARTIFACT_JSON=""
TEST_ARTIFACT_STATUS="missing"
TEST_ARTIFACT_RUN=""
COVERAGE_ARTIFACT_JSON=""
COVERAGE_ARTIFACT_STATUS="missing"
COVERAGE_ARTIFACT_RUN=""

_test_artifact_passed() {
  _load_test_artifact_status || return 1
  [ "$TEST_ARTIFACT_STATUS" = "pass" ]
}

_coverage_artifact_passed() {
  _load_coverage_artifact_status || return 1
  [ "$COVERAGE_ARTIFACT_STATUS" = "pass" ]
}

_check() {
  # _check <name> <regex>
  CHECKED=$((CHECKED + 1))
  if echo "$RESPONSE" | grep -qiE "$2"; then
    PASSED=$((PASSED + 1))
  elif echo "$1" | grep -qiE 'coverage|80_percent' && _coverage_artifact_passed; then
    # Coverage governance consumes the latest persisted coverage artifact.
    PASSED=$((PASSED + 1))
  elif echo "$1" | grep -qiE 'test' && _test_artifact_passed; then
    # Governance consumes the latest persisted cos-test/pytest-with-summary
    # artifacts instead of launching a fresh pytest run or trusting prose only.
    PASSED=$((PASSED + 1))
  else
    MISSING="${MISSING:+$MISSING, }$1"
  fi
}

case "$COMPLEXITY" in
  trivial)
    _check "code_compiles"    "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"
    _check "no_lint_errors"   "lint.*clean|lint.*pass|no.lint|0 issues|0 errors"
    ;;
  small)
    _check "code_compiles"    "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"
    _check "unit_tests_pass"  "tests? pass|PASS|all tests|test.*success|0 failed"
    _check "no_lint_errors"   "lint.*clean|lint.*pass|no.lint|0 issues|0 errors"
    ;;
  medium)
    _check "code_compiles"        "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"
    _check "unit_tests_added"     "new test|added test|test file|_test\.go|\.spec\.ts|test coverage"
    _check "coverage_maintained"  "coverage|cover.*[0-9]+%"
    _check "lint_clean"           "lint.*clean|lint.*pass|no.lint|0 issues|0 errors"
    _check "docs_updated"         "doc.*updated|README|\.md.*modified|documentation"
    ;;
  large)
    _check "readiness_check_pass"   "readiness.*pass|readiness.*PASS|prerequisites.*met"
    _check "code_compiles"          "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"
    _check "unit_tests_80_percent"  "coverage.*[8-9][0-9]%|coverage.*100%|80%|>= 80"
    _check "integration_tests"      "integration.*test|integration.*pass|e2e.*pass"
    _check "architecture_compliance" "architecture.*compliance|no.*violation|declared.framework|clean.arch"
    _check "docs_updated"           "doc.*updated|README|\.md.*modified|documentation"
    _check "adversarial_review"     "BLOCKER|CONCERN|SUGGESTION|adversarial.*review"
    ;;
  critical)
    _check "readiness_check_pass"   "readiness.*pass|readiness.*PASS|prerequisites.*met"
    _check "code_compiles"          "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"
    _check "unit_tests_80_percent"  "coverage.*[8-9][0-9]%|coverage.*100%|80%|>= 80"
    _check "integration_tests"      "integration.*test|integration.*pass|e2e.*pass"
    _check "architecture_compliance" "architecture.*compliance|no.*violation|declared.framework|clean.arch"
    _check "docs_updated"           "doc.*updated|README|\.md.*modified|documentation"
    _check "adversarial_review"     "BLOCKER|CONCERN|SUGGESTION|adversarial.*review"
    _check "security_review"        "security.*review|security.*assessment|vulnerability|threat"
    _check "idempotency_verified"   "idempoten|transaction.id|dedup|deduplicat"
    _check "audit_trail_present"    "audit.*trail|audit.*log|who.*when.*what|traceable"
    _check "rollback_tested"        "rollback.*test|rollback.*plan|rollback.*procedure|revert"
    ;;
esac

if [ -n "$MISSING" ]; then
  safe_jsonl_append "$DOD_LOG" "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"MISSING\",\"phase\":\"$PHASE\",\"complexity\":\"$COMPLEXITY\",\"enforcement\":\"$ENFORCEMENT\",\"checked\":$CHECKED,\"passed\":$PASSED,\"missing\":$(echo "$MISSING" | jq -Rs .)}"
  echo ""
  echo "=== DoD GATE: $ENFORCEMENT — Complexity: $COMPLEXITY ($PASSED/$CHECKED criteria met) ==="
  echo "Missing DoD criteria: $MISSING"
  if [ "$ENFORCEMENT" = "BLOCK" ]; then
    echo "NOTE: Phase '$PHASE' treats missing criteria as BLOCKING. Task should not be marked done."
  else
    echo "WARNING: Phase '$PHASE' — missing criteria noted (non-blocking)."
  fi
  echo "See: rules/definition-of-done.md"
  echo ""
else
  safe_jsonl_append "$DOD_LOG" "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"PASS\",\"phase\":\"$PHASE\",\"complexity\":\"$COMPLEXITY\",\"checked\":$CHECKED,\"passed\":$PASSED}"
fi

exit 0
