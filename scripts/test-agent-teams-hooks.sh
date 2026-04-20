#!/usr/bin/env bash
# SCOPE: os-only
# test-agent-teams-hooks.sh — Validate Agent Teams hooks with mock input.
#
# Usage: bash scripts/test-agent-teams-hooks.sh
#
# Runs each hook with simulated JSON stdin and reports pass/fail.
# This is a lightweight smoke test; for full coverage use:
#   python3 -m pytest tests/hooks/test_agent_teams_hooks.py -v

set -euo pipefail

HOOKS_DIR="$(cd "$(dirname "$0")/.." && pwd)/hooks"
PASS=0
FAIL=0
TOTAL=0

run_test() {
  local name="$1"
  local hook="$2"
  local input="$3"
  local expected_exit="$4"
  TOTAL=$((TOTAL + 1))

  local actual_exit=0
  echo "$input" | bash "$HOOKS_DIR/$hook" > /dev/null 2>&1 || actual_exit=$?

  if [ "$actual_exit" -eq "$expected_exit" ]; then
    PASS=$((PASS + 1))
    printf "  PASS  %-55s (exit %d)\n" "$name" "$actual_exit"
  else
    FAIL=$((FAIL + 1))
    printf "  FAIL  %-55s (expected %d, got %d)\n" "$name" "$expected_exit" "$actual_exit"
  fi
}

echo "=== Agent Teams Hook Validation ==="
echo ""

# ─── Registration Check ────────────────────────────────────────────────────

echo "--- Settings Registration ---"
python3 -c "
import json, sys
s = json.load(open('.claude/settings.json'))
ok = True
for event in ['TeammateIdle', 'TaskCreated', 'TaskCompleted']:
    if event in s.get('hooks', {}):
        print(f'  PASS  {event} registered in settings.json')
    else:
        print(f'  FAIL  {event} MISSING from settings.json')
        ok = False
sys.exit(0 if ok else 1)
" || FAIL=$((FAIL + 1))
echo ""

# ─── TeammateIdle ──────────────────────────────────────────────────────────

echo "--- TeammateIdle Hook ---"

run_test "valid JSON, no tasks file" \
  "teammate-idle.sh" \
  '{"hook_event_name": "TeammateIdle", "agent_id": "test-1"}' \
  0

run_test "empty stdin (graceful)" \
  "teammate-idle.sh" \
  '' \
  0

run_test "malformed JSON (graceful)" \
  "teammate-idle.sh" \
  '{{not valid}}' \
  0

echo ""

# ─── TaskCreated ───────────────────────────────────────────────────────────

echo "--- TaskCreated Hook ---"

run_test "valid task description" \
  "task-created.sh" \
  '{"hook_event_name": "TaskCreated", "description": "Implement auth endpoint with JWT validation"}' \
  0

run_test "short description (blocked)" \
  "task-created.sh" \
  '{"hook_event_name": "TaskCreated", "description": "fix"}' \
  2

run_test "no description field (graceful)" \
  "task-created.sh" \
  '{"hook_event_name": "TaskCreated", "agent_id": "test-1"}' \
  0

run_test "empty stdin (graceful)" \
  "task-created.sh" \
  '' \
  0

run_test "malformed JSON (graceful)" \
  "task-created.sh" \
  '{{bad json}}' \
  0

echo ""

# ─── TaskCompleted ─────────────────────────────────────────────────────────

echo "--- TaskCompleted Hook ---"

run_test "valid completion output" \
  "task-completed.sh" \
  '{"hook_event_name": "TaskCompleted", "output": "Implemented the endpoint. All 12 tests pass. Coverage at 85%."}' \
  0

run_test "short output (rejected)" \
  "task-completed.sh" \
  '{"hook_event_name": "TaskCompleted", "output": "done"}' \
  2

run_test "no output field (graceful)" \
  "task-completed.sh" \
  '{"hook_event_name": "TaskCompleted", "task_id": "abc"}' \
  0

run_test "empty stdin (graceful)" \
  "task-completed.sh" \
  '' \
  0

run_test "malformed JSON (graceful)" \
  "task-completed.sh" \
  'not valid json' \
  0

echo ""

# ─── Summary ───────────────────────────────────────────────────────────────

echo "=== Summary ==="
echo "  Total: $TOTAL | Pass: $PASS | Fail: $FAIL"

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "Some tests failed. Run the full pytest suite for details:"
  echo "  python3 -m pytest tests/hooks/test_agent_teams_hooks.py -v"
  exit 1
fi

echo ""
echo "All tests passed. For interactive testing, see docs/agent-teams-testing.md"
exit 0
