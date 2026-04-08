#!/usr/bin/env bash
# CONCERNS: quality, verification, testing
# Completion Gate Hook — PostToolUse for Agent
# Merged from: auto-verify.sh + dod-gate.sh + auto-refine.sh
# Single-pass agent output processing:
#   1. Checks acceptance criteria (auto-verify)
#   2. Checks Definition of Done (dod-gate)
#   3. If failures detected, suggests retry (auto-refine / PITER loop)
# Reads stdin ONCE instead of three separate processes.

set -uo pipefail

_HOOK_NAME="completion-gate"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
# Paperclip notification helper for safety mesh blocks (Gap 5)
_PAPERCLIP_LIB="$(dirname "$0")/_lib/paperclip-notify.sh"
[ -f "$_PAPERCLIP_LIB" ] && source "$_PAPERCLIP_LIB"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
[ ! -f "$CONFIG_FILE" ] && CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"

METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  _SESSION_FILE="$PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  [ -f "$_SESSION_FILE" ] && SESSION_ID=$(cat "$_SESSION_FILE" 2>/dev/null)
fi
if [ -n "$SESSION_ID" ]; then
  SESSION_METRICS="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/metrics"
  [ -d "$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID" ] && METRICS_DIR="$SESSION_METRICS"
fi

VERIFY_LOG="$METRICS_DIR/auto-verify.jsonl"
REFINE_DIR="$METRICS_DIR/auto-refine"
MAX_VERIFY_TIME=8
MAX_RETRIES=3

INPUT=$(cat)
[ -z "$INPUT" ] && exit 0
command -v jq &>/dev/null || exit 0

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[ "$TOOL_NAME" != "Agent" ] && exit 0

RESPONSE=$(echo "$INPUT" | jq -r '.tool_response // empty' 2>/dev/null)
if [ -z "$RESPONSE" ] || [ "$RESPONSE" = "null" ]; then
  RESPONSE=$(echo "$INPUT" | jq -r '.tool_response.result // .tool_response.output // .tool_response.content // empty' 2>/dev/null)
fi
[ -z "$RESPONSE" ] || [ "$RESPONSE" = "null" ] && exit 0

AGENT_PROMPT=$(echo "$INPUT" | jq -r '.tool_input.prompt // .tool_input.description // ""' 2>/dev/null)

PHASE="reconstruction"
if [ -f "$CONFIG_FILE" ]; then
  PARSED_PHASE=$(grep 'phase:' "$CONFIG_FILE" | head -1 | sed 's/.*phase:[[:space:]]*//' | sed 's/[[:space:]]*#.*//' | tr -d '[:space:]')
  [ -n "$PARSED_PHASE" ] && PHASE="$PARSED_PHASE"
fi

IS_COMPLETION=false
echo "$RESPONSE" | grep -qiE "done|complete|finished|implemented|fixed|resolved|delivered|all tasks|PASS|listo" && IS_COMPLETION=true

# === PHASE 1: ACCEPTANCE CRITERIA VERIFICATION ===
VERIFY_STATUS=""
VERIFY_FAILED=0

if [ "$IS_COMPLETION" = "true" ] && [ -n "$AGENT_PROMPT" ] && [ "$AGENT_PROMPT" != "null" ]; then
  if ! echo "$AGENT_PROMPT" | grep -qiE "ACCEPTANCE CRITERIA|acceptance criteria"; then
    mkdir -p "$METRICS_DIR" 2>/dev/null
    AGENT_DESC=$(echo "$AGENT_PROMPT" | head -c 100)
    safe_jsonl_append "$VERIFY_LOG" "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"NO_CRITERIA\",\"agent\":$(echo "$AGENT_DESC" | jq -Rs .),\"checks\":0,\"passed\":0,\"failed\":0}"
    echo ""; echo "=== COMPLETION-GATE: AUTO-VERIFY WARNING ==="; echo ""
    echo "No ACCEPTANCE CRITERIA defined in the agent prompt."
    echo "See: rules/acceptance-criteria.md"; echo ""
    VERIFY_STATUS="NO_CRITERIA"
  else
    CRITERIA_BLOCK=$(echo "$AGENT_PROMPT" | sed -n '/[Aa][Cc][Cc][Ee][Pp][Tt][Aa][Nn][Cc][Ee] [Cc][Rr][Ii][Tt][Ee][Rr][Ii][Aa]/,/^$/p' | tail -n +2)
    [ -z "$CRITERIA_BLOCK" ] && CRITERIA_BLOCK=$(echo "$AGENT_PROMPT" | awk '/[Aa][Cc][Cc][Ee][Pp][Tt][Aa][Nn][Cc][Ee] [Cc][Rr][Ii][Tt][Ee][Rr][Ii][Aa]/,/^[A-Z]/' | grep -E '^\s*[0-9]+\.' | head -20)
    if [ -z "$CRITERIA_BLOCK" ]; then
      VERIFY_STATUS="NO_PARSEABLE"
    else
      TOTAL_CHECKS=0; PASSED_CHECKS=0; FAILED_CHECKS=0; FAILED_DETAILS=""; PASS_DETAILS=""
      while IFS= read -r line; do
        [ -z "$line" ] && continue
        CRITERION_DESC=$(echo "$line" | sed 's/^\s*[0-9]*\.\s*//' | head -c 80)
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        if echo "$line" | grep -qE '`[^`]+`\s*=\s*[0-9]+'; then
          CMD=$(echo "$line" | grep -oE '`[^`]+`\s*=\s*[0-9]+' | head -1)
          VERIFY_CMD=$(echo "$CMD" | sed 's/`//g' | sed 's/\s*=\s*[0-9]*$//')
          EXPECTED=$(echo "$CMD" | grep -oE '[0-9]+$')
          if [ -n "$VERIFY_CMD" ] && [ -n "$EXPECTED" ]; then
            ACTUAL=$(cd "$PROJECT_DIR" && timeout "$MAX_VERIFY_TIME" bash -c "$VERIFY_CMD" 2>/dev/null | tr -d '[:space:]')
            if [ "$ACTUAL" = "$EXPECTED" ]; then PASSED_CHECKS=$((PASSED_CHECKS + 1)); PASS_DETAILS="${PASS_DETAILS}\n  PASS: $CRITERION_DESC"
            else FAILED_CHECKS=$((FAILED_CHECKS + 1)); FAILED_DETAILS="${FAILED_DETAILS}\n  FAIL: $CRITERION_DESC (actual=${ACTUAL:-<error>}, expected=$EXPECTED)"; fi; continue; fi; fi
        if echo "$line" | grep -qE '`[^`]+`\s*>=\s*[0-9]+'; then
          CMD=$(echo "$line" | grep -oE '`[^`]+`\s*>=\s*[0-9]+' | head -1)
          VERIFY_CMD=$(echo "$CMD" | sed 's/`//g' | sed 's/\s*>=\s*[0-9]*$//')
          THRESHOLD=$(echo "$CMD" | grep -oE '[0-9]+$')
          if [ -n "$VERIFY_CMD" ] && [ -n "$THRESHOLD" ]; then
            ACTUAL=$(cd "$PROJECT_DIR" && timeout "$MAX_VERIFY_TIME" bash -c "$VERIFY_CMD" 2>/dev/null | tr -d '[:space:]' | grep -oE '[0-9]+' | head -1)
            if [ -n "$ACTUAL" ] && [ "$ACTUAL" -ge "$THRESHOLD" ] 2>/dev/null; then PASSED_CHECKS=$((PASSED_CHECKS + 1)); PASS_DETAILS="${PASS_DETAILS}\n  PASS: $CRITERION_DESC"
            else FAILED_CHECKS=$((FAILED_CHECKS + 1)); FAILED_DETAILS="${FAILED_DETAILS}\n  FAIL: $CRITERION_DESC (actual=${ACTUAL:-<error>}, threshold=$THRESHOLD)"; fi; continue; fi; fi
        if echo "$line" | grep -qiE '`[^`]+`\s*exits?\s*0'; then
          VERIFY_CMD=$(echo "$line" | grep -oE '`[^`]+`' | head -1 | tr -d '`')
          if [ -n "$VERIFY_CMD" ]; then
            if cd "$PROJECT_DIR" && timeout "$MAX_VERIFY_TIME" bash -c "$VERIFY_CMD" &>/dev/null; then PASSED_CHECKS=$((PASSED_CHECKS + 1)); PASS_DETAILS="${PASS_DETAILS}\n  PASS: $CRITERION_DESC"
            else FAILED_CHECKS=$((FAILED_CHECKS + 1)); FAILED_DETAILS="${FAILED_DETAILS}\n  FAIL: $CRITERION_DESC (exit code $?, expected 0)"; fi; continue; fi; fi
        TOTAL_CHECKS=$((TOTAL_CHECKS - 1))
      done <<< "$CRITERIA_BLOCK"
      if [ "$TOTAL_CHECKS" -eq 0 ]; then VERIFY_STATUS="NO_PARSEABLE"
      elif [ "$FAILED_CHECKS" -gt 0 ]; then
        VERIFY_STATUS="FAIL"; VERIFY_FAILED=$FAILED_CHECKS
        safe_jsonl_append "$VERIFY_LOG" "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"FAIL\",\"agent\":$(echo "$AGENT_PROMPT" | head -c 100 | jq -Rs .),\"checks\":$TOTAL_CHECKS,\"passed\":$PASSED_CHECKS,\"failed\":$FAILED_CHECKS}"
        echo ""; echo "=== COMPLETION-GATE: VERIFICATION FAILED ==="; echo "Task is NOT complete. $FAILED_CHECKS of $TOTAL_CHECKS acceptance criteria FAILED."; echo -e "$PASS_DETAILS"; echo -e "$FAILED_DETAILS"; echo ""
      else
        VERIFY_STATUS="PASS"
        safe_jsonl_append "$VERIFY_LOG" "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"PASS\",\"agent\":$(echo "$AGENT_PROMPT" | head -c 100 | jq -Rs .),\"checks\":$TOTAL_CHECKS,\"passed\":$PASSED_CHECKS,\"failed\":0}"
        echo ""; echo "=== COMPLETION-GATE: VERIFICATION PASSED === ($PASSED_CHECKS/$TOTAL_CHECKS)"; echo ""
      fi
    fi
  fi
fi

# === PHASE 2: DEFINITION OF DONE CHECK ===
if [ "$IS_COMPLETION" = "true" ]; then
  COMPLEXITY=""
  echo "$RESPONSE" | grep -qiE "complexity:\s*trivial" && COMPLEXITY="trivial"
  echo "$RESPONSE" | grep -qiE "complexity:\s*small" && COMPLEXITY="small"
  echo "$RESPONSE" | grep -qiE "complexity:\s*medium" && COMPLEXITY="medium"
  echo "$RESPONSE" | grep -qiE "complexity:\s*large" && COMPLEXITY="large"
  echo "$RESPONSE" | grep -qiE "complexity:\s*critical" && COMPLEXITY="critical"
  if [ -z "$COMPLEXITY" ]; then
    echo "$RESPONSE" | grep -qiE "security|payment|migration|auth.change|encrypt" && COMPLEXITY="critical"
    echo "$RESPONSE" | grep -qiE "multi-service|cross-service|integration.test|sdk.package" && COMPLEXITY="large"
    echo "$RESPONSE" | grep -qiE "new feature|new endpoint|new use.case|refactor" && COMPLEXITY="medium"
  fi
  if [ -n "$COMPLEXITY" ]; then
    ENFORCEMENT="WARN"
    [ "$PHASE" = "production" ] || [ "$PHASE" = "maintenance" ] && ENFORCEMENT="BLOCK"
    MISSING=""; CHECKED=0; PASSED=0
    check_criterion() { CHECKED=$((CHECKED+1)); if echo "$RESPONSE" | grep -qiE "$2"; then PASSED=$((PASSED+1)); else MISSING="${MISSING:+$MISSING, }$1"; fi; }
    case "$COMPLEXITY" in
      trivial) check_criterion "code_compiles" "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"; check_criterion "no_lint_errors" "lint.*clean|lint.*pass|no.lint|0 issues|0 errors" ;;
      small) check_criterion "code_compiles" "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"; check_criterion "unit_tests_pass" "tests? pass|PASS|all tests|test.*success|0 failed"; check_criterion "no_lint_errors" "lint.*clean|lint.*pass|no.lint|0 issues|0 errors" ;;
      medium) check_criterion "code_compiles" "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"; check_criterion "unit_tests_added" "new test|added test|test file|_test\.go|\.spec\.ts|test coverage"; check_criterion "coverage_maintained" "coverage|cover.*[0-9]+%"; check_criterion "lint_clean" "lint.*clean|lint.*pass|no.lint|0 issues|0 errors"; check_criterion "docs_updated" "doc.*updated|README|\.md.*modified|documentation" ;;
      large) check_criterion "readiness_check_pass" "readiness.*pass|readiness.*PASS|prerequisites.*met"; check_criterion "code_compiles" "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"; check_criterion "unit_tests_80_percent" "coverage.*[8-9][0-9]%|coverage.*100%|80%|>= 80"; check_criterion "integration_tests" "integration.*test|integration.*pass|e2e.*pass"; check_criterion "architecture_compliance" "architecture.*compliance|no.*violation|ginext|clean.arch"; check_criterion "docs_updated" "doc.*updated|README|\.md.*modified|documentation"; check_criterion "adversarial_review" "BLOCKER|CONCERN|SUGGESTION|adversarial.*review" ;;
      critical) check_criterion "readiness_check_pass" "readiness.*pass|readiness.*PASS|prerequisites.*met"; check_criterion "code_compiles" "build.*success|compil.*success|exit.code.*0|BUILD SUCCESSFUL|no.errors"; check_criterion "unit_tests_80_percent" "coverage.*[8-9][0-9]%|coverage.*100%|80%|>= 80"; check_criterion "integration_tests" "integration.*test|integration.*pass|e2e.*pass"; check_criterion "architecture_compliance" "architecture.*compliance|no.*violation|ginext|clean.arch"; check_criterion "docs_updated" "doc.*updated|README|\.md.*modified|documentation"; check_criterion "adversarial_review" "BLOCKER|CONCERN|SUGGESTION|adversarial.*review"; check_criterion "security_review" "security.*review|security.*assessment|vulnerability|threat"; check_criterion "idempotency_verified" "idempoten|transaction.id|dedup|deduplicat"; check_criterion "audit_trail_present" "audit.*trail|audit.*log|who.*when.*what|traceable"; check_criterion "rollback_tested" "rollback.*test|rollback.*plan|rollback.*procedure|revert" ;;
    esac
    if [ -n "$MISSING" ]; then
      echo ""; echo "--- DoD Gate: $ENFORCEMENT — Complexity: $COMPLEXITY ($PASSED/$CHECKED criteria met) ---"
      echo "Missing DoD criteria: $MISSING"
      [ "$ENFORCEMENT" = "BLOCK" ] && echo "BLOCKED: Phase is $PHASE. Task CANNOT be marked as done until all criteria pass." || echo "WARNING: Phase is $PHASE. Missing criteria noted but not blocking."
      echo ""
    fi
  fi
fi

# === PHASE 3: AUTO-REFINE / PITER LOOP ===
AUTO_REFINE_MODE="auto"
case "$PHASE" in reconstruction|stabilization) AUTO_REFINE_MODE="auto" ;; production|maintenance) AUTO_REFINE_MODE="suggest" ;; esac

AGENT_ID=$(echo "$INPUT" | jq -r '.tool_input.description // .tool_input.prompt // "unknown"' 2>/dev/null | head -c 100)
TASK_FINGERPRINT=$(echo "$AGENT_ID" | head -c 50 | md5 2>/dev/null || echo "$AGENT_ID" | head -c 50 | md5sum 2>/dev/null | cut -d' ' -f1 || echo "unknown")
AGENT_OUTPUT=$(echo "$INPUT" | jq -r '.tool_response.result // .tool_response.output // .tool_response.content // ""' 2>/dev/null)
[ -z "$AGENT_OUTPUT" ] || [ "$AGENT_OUTPUT" = "null" ] && AGENT_OUTPUT="$RESPONSE"

FAILURE_DETECTED=false; FAILURE_TYPE=""; FAILURE_DETAILS=""
[ "$VERIFY_STATUS" = "FAIL" ] && [ "$VERIFY_FAILED" -gt 0 ] && FAILURE_DETECTED=true && FAILURE_TYPE="ACCEPTANCE_CRITERIA_FAILURE" && FAILURE_DETAILS="$VERIFY_FAILED acceptance criteria checks failed"
echo "$AGENT_OUTPUT" | grep -qiE '(FAIL|FAILED|test.*fail|failing test|tests? failed|assertion.*error|expect.*received)' && FAILURE_DETECTED=true && [ -z "$FAILURE_TYPE" ] && FAILURE_TYPE="TEST_FAILURE" && FAILURE_DETAILS=$(echo "$AGENT_OUTPUT" | grep -iE '(FAIL|FAILED|Error|expect|assertion)' | head -5)
echo "$AGENT_OUTPUT" | grep -qiE '(build failed|compilation error|compile error|cannot find|syntax error|type error|TS[0-9]{4}|cannot resolve|module not found)' && FAILURE_DETECTED=true && [ -z "$FAILURE_TYPE" ] && FAILURE_TYPE="BUILD_ERROR" && FAILURE_DETAILS=$(echo "$AGENT_OUTPUT" | grep -iE '(error|cannot|undefined|syntax)' | head -5)
echo "$AGENT_OUTPUT" | grep -qiE '(lint error|linting failed|eslint.*error|golangci-lint.*error)' && FAILURE_DETECTED=true && [ -z "$FAILURE_TYPE" ] && FAILURE_TYPE="LINT_ERROR" && FAILURE_DETAILS=$(echo "$AGENT_OUTPUT" | grep -iE '(error|warning|lint)' | head -5)
echo "$INPUT" | jq -e '.tool_response.error // .tool_response.is_error' &>/dev/null 2>&1 && FAILURE_DETECTED=true && [ -z "$FAILURE_TYPE" ] && FAILURE_TYPE="AGENT_ERROR" && FAILURE_DETAILS=$(echo "$AGENT_OUTPUT" | head -5)

if [ "$FAILURE_DETECTED" = false ]; then
  if [ -d "$REFINE_DIR" ] && [ -f "$REFINE_DIR/$TASK_FINGERPRINT.count" ]; then
    rm -f "$REFINE_DIR/$TASK_FINGERPRINT.count" "$REFINE_DIR/$TASK_FINGERPRINT.history" 2>/dev/null
  fi
  # Wire to learning pipeline (success path)
  echo "$INPUT" | python3 "$PROJECT_DIR/lib/record_completion.py" 2>/dev/null || true
  exit 0
fi

mkdir -p "$REFINE_DIR" 2>/dev/null
RETRY_FILE="$REFINE_DIR/$TASK_FINGERPRINT.count"
RETRY_COUNT=0
[ -f "$RETRY_FILE" ] && RETRY_COUNT=$(cat "$RETRY_FILE" 2>/dev/null || echo "0")
[[ "$RETRY_COUNT" =~ ^[0-9]+$ ]] || RETRY_COUNT=0
RETRY_COUNT=$((RETRY_COUNT + 1))
echo "$RETRY_COUNT" > "$RETRY_FILE"
safe_jsonl_append "$REFINE_DIR/$TASK_FINGERPRINT.history" "{\"attempt\":$RETRY_COUNT,\"type\":\"$FAILURE_TYPE\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"details\":$(echo "$FAILURE_DETAILS" | head -c 200 | jq -Rs .)}"

if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
  echo ""; echo "=== COMPLETION-GATE: ESCALATION REQUIRED ==="
  echo "Agent task failed after $MAX_RETRIES attempts. Human intervention needed."
  echo "Task: $AGENT_ID"; echo "Failure type: $FAILURE_TYPE"
  echo "Latest error:"; echo "$FAILURE_DETAILS" | head -5
  echo "=== END ESCALATION ==="; echo ""
  rm -f "$RETRY_FILE" "$REFINE_DIR/$TASK_FINGERPRINT.history" 2>/dev/null
  exit 0
fi

if [ "$AUTO_REFINE_MODE" = "suggest" ]; then
  echo ""; echo "=== COMPLETION-GATE: FAILURE DETECTED (phase: $PHASE) ==="
  echo "Agent task failed (attempt $RETRY_COUNT/$MAX_RETRIES). Failure type: $FAILURE_TYPE"
  echo "Phase '$PHASE' requires human approval for auto-refinement."
  echo "=== END COMPLETION-GATE ==="; echo ""
  exit 0
fi

echo ""; echo "=== COMPLETION-GATE: RETRY $RETRY_COUNT/$MAX_RETRIES ==="
echo "ORCHESTRATOR ACTION REQUIRED: Re-launch the agent with this context:"
echo "---"; echo "PITER REFINEMENT (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
echo "Previous attempt failed with $FAILURE_TYPE:"; echo "$FAILURE_DETAILS" | head -5
echo "Instructions:"; echo "1. Analyze WHY the previous attempt failed"
echo "2. Fix the root cause (not just symptoms)"; echo "3. Re-run verification to confirm the fix"
[ "$RETRY_COUNT" -ge 2 ] && echo "4. LAST ATTEMPT — if this fails, escalate with full diagnosis"
echo "---"; echo "=== END COMPLETION-GATE ==="; echo ""

# Wire to learning pipeline
echo "$INPUT" | python3 "$PROJECT_DIR/lib/record_completion.py" 2>/dev/null || true

exit 0
