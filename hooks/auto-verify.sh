#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: quality, verification, acceptance-criteria
# Auto-Verify Hook — PostToolUse for Agent
# Extracts ACCEPTANCE CRITERIA from the agent prompt or response, runs each
# verification command, and logs PASS/FAIL to auto-verify.jsonl.
# Non-blocking (advisory): always exits 0. The orchestrator reads output
# to decide whether to re-launch the agent.
#
# Contract: described in rules/acceptance-criteria.md and rules/agent-quality.md.
# Related: completion-gate.sh performs the same logic as part of a larger
# 3-phase pipeline. This standalone hook exists for users that register
# auto-verify separately (or invoke it directly).
#
# Reads tool_name / tool_response / tool_input from the standard Agent hook payload.
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="auto-verify"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

INPUT=$(cat)
[ -z "$INPUT" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[ "$TOOL_NAME" != "Agent" ] && exit 0

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"

# Resolve session-scoped metrics dir (fall back to global)
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  _SESSION_FILE="$PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  [ -f "$_SESSION_FILE" ] && SESSION_ID=$(cat "$_SESSION_FILE" 2>/dev/null)
fi
if [ -n "$SESSION_ID" ] && [ -d "$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID" ]; then
  METRICS_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/metrics"
fi

VERIFY_LOG="$METRICS_DIR/auto-verify.jsonl"
MAX_VERIFY_TIME=8

RESPONSE=$(echo "$INPUT" | jq -r '.tool_response // empty' 2>/dev/null)
if [ -z "$RESPONSE" ] || [ "$RESPONSE" = "null" ]; then
  RESPONSE=$(echo "$INPUT" | jq -r '.tool_response.result // .tool_response.output // .tool_response.content // empty' 2>/dev/null)
fi
[ -z "$RESPONSE" ] || [ "$RESPONSE" = "null" ] && exit 0

AGENT_PROMPT=$(echo "$INPUT" | jq -r '.tool_input.prompt // .tool_input.description // ""' 2>/dev/null)

# Only run when the agent claims completion
IS_COMPLETION=false
echo "$RESPONSE" | grep -qiE "done|complete|finished|implemented|fixed|resolved|delivered|all tasks|PASS|listo" && IS_COMPLETION=true
[ "$IS_COMPLETION" = "true" ] || exit 0

# Pick the criteria source: prompt first (originator), then response (agent self-defined)
CRITERIA_SOURCE=""
if echo "$AGENT_PROMPT" | grep -qiE "ACCEPTANCE CRITERIA|acceptance criteria"; then
  CRITERIA_SOURCE="$AGENT_PROMPT"
elif echo "$RESPONSE" | grep -qiE "ACCEPTANCE CRITERIA|acceptance criteria"; then
  CRITERIA_SOURCE="$RESPONSE"
fi

mkdir -p "$METRICS_DIR" 2>/dev/null
AGENT_DESC=$(echo "$AGENT_PROMPT" | head -c 100)
TEST_ARTIFACT_JSON=""
TEST_ARTIFACT_STATUS="missing"
TEST_ARTIFACT_RUN=""

_load_test_artifact_status() {
  [ -n "$TEST_ARTIFACT_JSON" ] && return 0
  local helper="$PROJECT_DIR/scripts/cos_test_artifact_status.py"
  [ -f "$helper" ] || return 1
  TEST_ARTIFACT_JSON=$(python3 "$helper" --project-root "$PROJECT_DIR" --json 2>/dev/null || true)
  [ -n "$TEST_ARTIFACT_JSON" ] || return 1
  TEST_ARTIFACT_STATUS=$(echo "$TEST_ARTIFACT_JSON" | jq -r '.status // "missing"' 2>/dev/null)
  TEST_ARTIFACT_RUN=$(echo "$TEST_ARTIFACT_JSON" | jq -r '.run_dir // ""' 2>/dev/null)
  [ "$TEST_ARTIFACT_STATUS" != "missing" ]
}

if [ -z "$CRITERIA_SOURCE" ]; then
  safe_jsonl_append "$VERIFY_LOG" "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"NO_CRITERIA\",\"agent\":$(echo "$AGENT_DESC" | jq -Rs .),\"checks\":0,\"passed\":0,\"failed\":0}"
  echo ""
  echo "=== AUTO-VERIFY: NO ACCEPTANCE CRITERIA ==="
  echo "Agent prompt did not include an ACCEPTANCE CRITERIA block."
  echo "See: rules/acceptance-criteria.md"
  echo ""
  exit 0
fi

# Extract the ACCEPTANCE CRITERIA block (numbered or bulleted items under the header)
CRITERIA_BLOCK=$(echo "$CRITERIA_SOURCE" | awk '
  /^[[:space:]]*(#{1,3}[[:space:]]+)?[Aa]cceptance[[:space:]][Cc]riteria/ ||
  /^[[:space:]]*ACCEPTANCE[[:space:]]CRITERIA/ {
    found=1; next
  }
  found {
    if (/^[[:space:]]*(#{1,4})[[:space:]]/ ||
        /^[[:space:]]*[A-Z]{4,}[[:space:]:]/ ||
        /^[[:space:]]*[A-Z]{4,}$/ ||
        /^[=]{3,}/ ||
        /^[-]{3,}[[:space:]]*$/) {
      exit
    }
    if (/^[[:space:]]*([0-9]+\.|-|\*)[[:space:]]/) print
  }
')

if [ -z "$CRITERIA_BLOCK" ]; then
  safe_jsonl_append "$VERIFY_LOG" "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"NO_PARSEABLE\",\"agent\":$(echo "$AGENT_DESC" | jq -Rs .),\"checks\":0,\"passed\":0,\"failed\":0}"
  echo ""
  echo "=== AUTO-VERIFY: ACCEPTANCE CRITERIA PRESENT BUT NOT PARSEABLE ==="
  echo "Header found but no numbered or bulleted items followed."
  echo ""
  exit 0
fi

TOTAL=0; PASSED=0; FAILED=0; SKIPPED=0
FAIL_LINES=""; PASS_LINES=""; SKIP_LINES=""

_run_cmd() {
  # Runs a command with timeout in the project dir; echoes stdout; exit code in $?
  cd "$PROJECT_DIR" && timeout "$MAX_VERIFY_TIME" bash -c "$1" 2>/dev/null
}

while IFS= read -r line; do
  [ -z "$line" ] && continue
  DESC=$(echo "$line" | sed 's/^[[:space:]]*[0-9]*\.[[:space:]]*//' | sed 's/^[[:space:]]*[-*][[:space:]]*//' | head -c 100)
  TOTAL=$((TOTAL + 1))

  # Pattern 0: test evidence criteria consume persisted artifacts instead of
  # launching pytest/cos-test again from a governance hook.
  if echo "$line" | grep -qiE '(test|pytest|cos-test|junit|inventory|summary).*(pass|passed|0 failed|no failures|green)' || \
     echo "$line" | grep -qiE '(pass|passed|0 failed|no failures|green).*(test|pytest|cos-test|junit|inventory|summary)'; then
    if _load_test_artifact_status; then
      if [ "$TEST_ARTIFACT_STATUS" = "pass" ]; then
        PASSED=$((PASSED + 1)); PASS_LINES="${PASS_LINES}
  PASS: $DESC (artifact: $TEST_ARTIFACT_RUN)"
      else
        FAILED=$((FAILED + 1)); FAIL_LINES="${FAIL_LINES}
  FAIL: $DESC (artifact status=$TEST_ARTIFACT_STATUS, run=$TEST_ARTIFACT_RUN)"
      fi
    else
      SKIPPED=$((SKIPPED + 1)); TOTAL=$((TOTAL - 1)); SKIP_LINES="${SKIP_LINES}
  SKIP: $DESC (no persisted test artifact found)"
    fi
    continue
  fi

  # Pattern A: `cmd` = N  (exact numeric match)
  if echo "$line" | grep -qE '`[^`]+`[[:space:]]*=[[:space:]]*[0-9]+'; then
    CMD=$(echo "$line" | grep -oE '`[^`]+`[[:space:]]*=[[:space:]]*[0-9]+' | head -1)
    VCMD=$(echo "$CMD" | sed 's/`//g' | sed 's/[[:space:]]*=[[:space:]]*[0-9]*$//')
    EXPECT=$(echo "$CMD" | grep -oE '[0-9]+$')
    if [ -n "$VCMD" ] && [ -n "$EXPECT" ]; then
      ACTUAL=$(_run_cmd "$VCMD" | tr -d '[:space:]')
      if [ "$ACTUAL" = "$EXPECT" ]; then
        PASSED=$((PASSED + 1)); PASS_LINES="${PASS_LINES}\n  PASS: $DESC"
      else
        FAILED=$((FAILED + 1)); FAIL_LINES="${FAIL_LINES}\n  FAIL: $DESC (actual=${ACTUAL:-<error>}, expected=$EXPECT)"
      fi
      continue
    fi
  fi

  # Pattern B: `cmd` >= N  (threshold)
  if echo "$line" | grep -qE '`[^`]+`[[:space:]]*>=[[:space:]]*[0-9]+'; then
    CMD=$(echo "$line" | grep -oE '`[^`]+`[[:space:]]*>=[[:space:]]*[0-9]+' | head -1)
    VCMD=$(echo "$CMD" | sed 's/`//g' | sed 's/[[:space:]]*>=[[:space:]]*[0-9]*$//')
    THR=$(echo "$CMD" | grep -oE '[0-9]+$')
    if [ -n "$VCMD" ] && [ -n "$THR" ]; then
      ACTUAL=$(_run_cmd "$VCMD" | tr -d '[:space:]' | grep -oE '[0-9]+' | head -1)
      if [ -n "$ACTUAL" ] && [ "$ACTUAL" -ge "$THR" ] 2>/dev/null; then
        PASSED=$((PASSED + 1)); PASS_LINES="${PASS_LINES}\n  PASS: $DESC"
      else
        FAILED=$((FAILED + 1)); FAIL_LINES="${FAIL_LINES}\n  FAIL: $DESC (actual=${ACTUAL:-<error>}, threshold=$THR)"
      fi
      continue
    fi
  fi

  # Pattern C: `cmd` exits 0 / should exit 0
  if echo "$line" | grep -qiE '`[^`]+`[[:space:]]*(should[[:space:]]+)?(exit|return)s?[[:space:]]*0'; then
    VCMD=$(echo "$line" | grep -oE '`[^`]+`' | head -1 | tr -d '`')
    if [ -n "$VCMD" ]; then
      if _run_cmd "$VCMD" >/dev/null 2>&1; then
        PASSED=$((PASSED + 1)); PASS_LINES="${PASS_LINES}\n  PASS: $DESC"
      else
        FAILED=$((FAILED + 1)); FAIL_LINES="${FAIL_LINES}\n  FAIL: $DESC (exit code non-zero)"
      fi
      continue
    fi
  fi

  # Pattern D: `cmd` returns empty / should produce no output
  if echo "$line" | grep -qiE '`[^`]+`[[:space:]]*(should[[:space:]]+)?(return|returns|produce)s?[[:space:]]*(empty|nothing|no[[:space:]]+output)'; then
    VCMD=$(echo "$line" | grep -oE '`[^`]+`' | head -1 | tr -d '`')
    if [ -n "$VCMD" ]; then
      ACTUAL=$(_run_cmd "$VCMD")
      if [ -z "$ACTUAL" ]; then
        PASSED=$((PASSED + 1)); PASS_LINES="${PASS_LINES}\n  PASS: $DESC"
      else
        FAILED=$((FAILED + 1)); FAIL_LINES="${FAIL_LINES}\n  FAIL: $DESC (expected empty, got: ${ACTUAL:0:60})"
      fi
      continue
    fi
  fi

  # Not parseable as a check — record SKIP
  SKIPPED=$((SKIPPED + 1))
  TOTAL=$((TOTAL - 1))
  SKIP_LINES="${SKIP_LINES}\n  SKIP: $DESC"
done <<< "$CRITERIA_BLOCK"

if [ "$TOTAL" -eq 0 ] && [ "$SKIPPED" -gt 0 ]; then
  safe_jsonl_append "$VERIFY_LOG" "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"NO_PARSEABLE\",\"agent\":$(echo "$AGENT_DESC" | jq -Rs .),\"checks\":0,\"passed\":0,\"failed\":0,\"skipped\":$SKIPPED}"
  echo ""
  echo "=== AUTO-VERIFY: NONE OF $SKIPPED CRITERIA WERE PARSEABLE ==="
  echo -e "$SKIP_LINES"
  echo ""
  exit 0
fi

if [ "$FAILED" -gt 0 ]; then
  STATUS="FAIL"
  safe_jsonl_append "$VERIFY_LOG" "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"FAIL\",\"agent\":$(echo "$AGENT_DESC" | jq -Rs .),\"checks\":$TOTAL,\"passed\":$PASSED,\"failed\":$FAILED,\"skipped\":$SKIPPED}"
  echo ""
  echo "=== AUTO-VERIFY: $FAILED of $TOTAL ACCEPTANCE CRITERIA FAILED ==="
  echo -e "$PASS_LINES"
  echo -e "$FAIL_LINES"
  [ -n "$SKIP_LINES" ] && echo -e "$SKIP_LINES"
  echo ""
else
  safe_jsonl_append "$VERIFY_LOG" "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"PASS\",\"agent\":$(echo "$AGENT_DESC" | jq -Rs .),\"checks\":$TOTAL,\"passed\":$PASSED,\"failed\":0,\"skipped\":$SKIPPED}"
  echo ""
  echo "=== AUTO-VERIFY: PASS ($PASSED/$TOTAL) ==="
  [ -n "$PASS_LINES" ] && echo -e "$PASS_LINES"
  [ "$SKIPPED" -gt 0 ] && echo "  ($SKIPPED criteria skipped — no parseable command found)"
  echo ""
fi

exit 0
